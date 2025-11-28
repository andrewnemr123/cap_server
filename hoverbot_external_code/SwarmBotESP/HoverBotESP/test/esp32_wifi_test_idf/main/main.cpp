#include <string>
#include <cstring>
#include <cstdio>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_err.h"
#include "lwip/inet.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include <strings.h>

static const char *TAG = "esp32_wifi_test";

// ---- CONFIG: default hotspot credentials (you can change or set via serial) ----
static char WIFI_SSID[64] = "PatwickIphone";
static char WIFI_PASSWORD[64] = "hello111";
// ------------------------------------------------------------------------------

static const int LED_GPIO = 2;
static EventGroupHandle_t s_wifi_event_group;
const int WIFI_CONNECTED_BIT = BIT0;

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START)
    {
        esp_wifi_connect();
    }
    else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED)
    {
        ESP_LOGI(TAG, "Disconnected. Trying to reconnect...");
        esp_wifi_connect();
        xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
    else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP)
    {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

static void wifi_init_sta()
{
    s_wifi_event_group = xEventGroupCreate();

    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, &instance_any_id);
    esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, &instance_got_ip);

    wifi_config_t wifi_config;
    memset(&wifi_config, 0, sizeof(wifi_config));
    strncpy((char *)wifi_config.sta.ssid, WIFI_SSID, sizeof(wifi_config.sta.ssid) - 1);
    strncpy((char *)wifi_config.sta.password, WIFI_PASSWORD, sizeof(wifi_config.sta.password) - 1);

    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();
}

static void scan_and_print()
{
    wifi_scan_config_t scan_config = {};
    scan_config.show_hidden = true;

    ESP_ERROR_CHECK(esp_wifi_scan_start(&scan_config, true)); // blocking
    uint16_t ap_num = 0;
    esp_wifi_scan_get_ap_num(&ap_num);
    wifi_ap_record_t *ap_records = (wifi_ap_record_t *)malloc(sizeof(wifi_ap_record_t) * ap_num);
    if (!ap_records)
    {
        ESP_LOGE(TAG, "Failed to allocate memory for AP records");
        return;
    }
    esp_wifi_scan_get_ap_records(&ap_num, ap_records);
    ESP_LOGI(TAG, "Found %u APs:", ap_num);
    for (int i = 0; i < ap_num; ++i)
    {
        ESP_LOGI(TAG, "%d: %s (RSSI: %d) %s", i + 1, ap_records[i].ssid, ap_records[i].rssi, (ap_records[i].authmode == WIFI_AUTH_OPEN) ? "OPEN" : "SECURED");
    }
    free(ap_records);
}

static void attempt_connect_with_timeout(uint32_t timeout_ms)
{
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdFALSE, pdMS_TO_TICKS(timeout_ms));
    if (bits & WIFI_CONNECTED_BIT)
    {
        ESP_LOGI(TAG, "Connected to %s", WIFI_SSID);
    }
    else
    {
        ESP_LOGI(TAG, "Failed to connect within %u ms", timeout_ms);
        scan_and_print();
    }
}

extern "C" void app_main(void)
{
    // init NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND)
    {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Serial console via UART0 is already available via ESP_LOG
    esp_log_level_set(TAG, ESP_LOG_INFO);

    // Install UART driver for reading console input
    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .rx_flow_ctrl_thresh = 0,
        .source_clk = UART_SCLK_DEFAULT,
        .flags = 0,
    };
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM_0, 1024, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(UART_NUM_0, &uart_config));

    // configure LED
    gpio_reset_pin((gpio_num_t)LED_GPIO);
    gpio_set_direction((gpio_num_t)LED_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level((gpio_num_t)LED_GPIO, 0);

    ESP_LOGI(TAG, "ESP32 WiFi hotspot test");
    ESP_LOGI(TAG, "Default SSID: %s", WIFI_SSID);

    wifi_init_sta();
    attempt_connect_with_timeout(20000);

    // create a simple task to handle console (uart0) input and LED blink
    xTaskCreate([](void *)
                {
        const TickType_t delayMs = pdMS_TO_TICKS(10);
        TickType_t lastBlink = xTaskGetTickCount();
        bool ledState = false;
        char linebuf[128];
        while (true) {
            // Blink when connected
            if (xEventGroupGetBits(s_wifi_event_group) & WIFI_CONNECTED_BIT) {
                if (xTaskGetTickCount() - lastBlink > pdMS_TO_TICKS(500)) {
                    ledState = !ledState;
                    gpio_set_level((gpio_num_t)LED_GPIO, ledState ? 1 : 0);
                    lastBlink = xTaskGetTickCount();
                }
            } else {
                gpio_set_level((gpio_num_t)LED_GPIO, 0);
            }

            // Read from UART0 (stdin) non-blocking
            int len = uart_read_bytes(UART_NUM_0, (uint8_t *)linebuf, sizeof(linebuf) - 1, 20 / portTICK_PERIOD_MS);
            if (len > 0) {
                linebuf[len] = '\0';
                // remove trailing newlines and spaces
                while (len > 0 && (linebuf[len - 1] == '\n' || linebuf[len - 1] == '\r' || linebuf[len - 1] == ' ')) {
                    linebuf[--len] = '\0';
                }
                if (len > 0) {
                    // parse commands
                    char *comma = strchr(linebuf, ',');
                    if (comma) {
                        *comma = '\0';
                        char *ssid = linebuf;
                        char *pass = comma + 1;
                        strncpy(WIFI_SSID, ssid, sizeof(WIFI_SSID) - 1);
                        WIFI_SSID[sizeof(WIFI_SSID) - 1] = '\0';
                        strncpy(WIFI_PASSWORD, pass, sizeof(WIFI_PASSWORD) - 1);
                        WIFI_PASSWORD[sizeof(WIFI_PASSWORD) - 1] = '\0';
                        ESP_LOGI(TAG, "New credentials set: '%s' / '%s'", WIFI_SSID, WIFI_PASSWORD);
                        // reconfigure WiFi
                        wifi_config_t wifi_config;
                        memset(&wifi_config, 0, sizeof(wifi_config));
                        strncpy((char *)wifi_config.sta.ssid, WIFI_SSID, sizeof(wifi_config.sta.ssid) - 1);
                        strncpy((char *)wifi_config.sta.password, WIFI_PASSWORD, sizeof(wifi_config.sta.password) - 1);
                        esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
                        esp_wifi_disconnect();
                        esp_wifi_connect();
                        attempt_connect_with_timeout(20000);
                    } else if (strcasecmp(linebuf, "status") == 0) {
                        EventBits_t bits = xEventGroupGetBits(s_wifi_event_group);
                        if (bits & WIFI_CONNECTED_BIT) {
                            // get IP
                            esp_netif_ip_info_t ipinfo;
                            esp_netif_get_ip_info(esp_netif_get_handle_from_ifkey("WIFI_STA_DEF"), &ipinfo);
                            ESP_LOGI(TAG, "== WiFi connected ==");
                            ESP_LOGI(TAG, "SSID: %s", WIFI_SSID);
                            ESP_LOGI(TAG, "IP: " IPSTR, IP2STR(&ipinfo.ip));
                            // get RSSI
                            wifi_ap_record_t apinfo;
                            if (esp_wifi_sta_get_ap_info(&apinfo) == ESP_OK) {
                                ESP_LOGI(TAG, "RSSI: %d dBm", apinfo.rssi);
                            }
                        } else {
                            ESP_LOGI(TAG, "WiFi not connected");
                        }
                    } else if (strcasecmp(linebuf, "scan") == 0) {
                        scan_and_print();
                    } else {
                        ESP_LOGI(TAG, "Unrecognized command. Use: ssid,password OR 'scan' OR 'status'");
                    }
                }
            }

            vTaskDelay(delayMs);
        } }, "console_task", 4096, NULL, 5, NULL);
}
