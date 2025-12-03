#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <driver/gpio.h>
#include <driver/uart.h>
#include <sdkconfig.h>
#include <cJSON.h>
#include <string.h>
#include <math.h>
#include "main.h"

// fast scan
#include <esp_wifi.h>
#include <esp_event.h>
#include <nvs_flash.h>

// tcp_client
#include <sys/socket.h>
#include <errno.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <esp_netif.h>
#include <esp_timer.h>

// robot drivers
#include "motor_driver.h"

// Global configuration values read from NVS (non-volatile storage).
// These are pointers to heap-allocated C-strings and a 16-bit port number.
// They represent the Wi-Fi SSID/password, the server host/port, and the
// robot identity string that is sent to the server for registration.
char *g_ssid;
char *g_pwd;
char *g_server_host;
uint16_t g_server_port;
char *g_identity;

// server message format
// Example JSON message used for a quick runtime test of cJSON parsing.
// This string is parsed in `app_main` to verify JSON support.
static const char *MSG_TEST_1 = "{\"id\":1,\"command\":\"FORWARD\",\"status\":\"DISPATCHED\",\"intData\":[],\"floatData\":[123.456, 99.9, 15.23],\"result\":0.0,\"text\":\"\"}";

// Forward declaration: main TCP client loop that connects to the server,
// receives commands, executes robot actions and sends back responses.
void tcp_client(void);

// WiFi / IP event handler used by the ESP-IDF event loop.
// - On WIFI_EVENT_STA_START: trigger a connection attempt.
// - On WIFI_EVENT_STA_DISCONNECTED: try reconnecting.
// - On IP_EVENT_STA_GOT_IP: log the assigned IP and start the TCP client.
// This decouples network bring-up from the TCP client so the client only
// runs once an IP address has been obtained.
static void event_handler(void *arg, esp_event_base_t event_base,
						  int32_t event_id, void *event_data)
{
	if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START)
	{
		// Station interface started — attempt to connect to configured AP
		esp_wifi_connect();
	}
	else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED)
	{
		// Lost connection — try to reconnect automatically
		esp_wifi_connect();
	}
	else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP)
	{
		// Successfully obtained an IP; start the TCP client loop
		ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
		ESP_LOGI(TAG_WIFI, "got ip:" IPSTR, IP2STR(&event->ip_info.ip));
		tcp_client();
	}
}

void fast_scan()
{
	ESP_ERROR_CHECK(esp_netif_init());
	ESP_ERROR_CHECK(esp_event_loop_create_default());

	wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
	ESP_ERROR_CHECK(esp_wifi_init(&cfg));

	ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &event_handler, NULL, NULL));
	ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &event_handler, NULL, NULL));

	// Create default WiFi station network interface (esp-netif manages TCP/IP)
	// The returned pointer is rarely used directly by app code, but the call
	// registers and configures the default WiFi station interface used below.
	esp_netif_t *sta_netif = esp_netif_create_default_wifi_sta();
	assert(sta_netif);

	// Prepare station configuration using values loaded from NVS.
	// NOTE: wifi_config_t contains fixed-size arrays for SSID/password,
	// so we copy the heap strings into those buffers before starting.
	wifi_config_t wifi_config = {
		.sta = {
			.scan_method = DEFAULT_SCAN_METHOD,
			.sort_method = DEFAULT_SORT_METHOD,
			.threshold.rssi = DEFAULT_RSSI,
			.threshold.authmode = DEFAULT_AUTHMODE,
		},
	};
	strcpy((char *)wifi_config.sta.ssid, (char *)g_ssid);
	strcpy((char *)wifi_config.sta.password, (char *)g_pwd);
	ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
	ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
	ESP_ERROR_CHECK(esp_wifi_start());
}

int msg_send(int sock, const char *tx, int tx_len)
{
	// send() can return less bytes than supplied length.
	// Walk-around for robust implementation.
	int to_write = tx_len;
	while (to_write > 0)
	{
		int written = send(sock, tx + (tx_len - to_write), to_write, 0);
		if (written < 0)
		{
			ESP_LOGE(TAG_TCP, "Error occurred during sending: errno %d", errno);
			// Failed to retransmit, giving up
			return errno;
		}
		to_write -= written;
	}
	return 0; // no error if return 0
}

int msg_recv(int sock, char *rx_buf, int rx_buf_size)
{
	int rx_len = recv(sock, rx_buf, rx_buf_size - 1, 0);
	if (rx_len < 0)
	{
		ESP_LOGE(TAG_TCP, "Error occurred during receiving: errno %d", errno);
	}
	else if (rx_len == 0)
	{
		ESP_LOGW(TAG_TCP, "Connection closed");
	}
	else
	{
		rx_buf[rx_len] = 0;
		ESP_LOGI(TAG_TCP, "Received %d bytes from %s:", rx_len, g_server_host);
		ESP_LOGI(TAG_TCP, "%s", rx_buf);
	}
	return rx_len; // success if rx_len > 0
}

// UDP sensor streaming task
// This FreeRTOS task runs in parallel with TCP command handling
// Periodically samples ultrasonic sensor and sends UDP packets to server
typedef struct
{
	int sock;
	struct sockaddr_in dest_addr;
} udp_task_params_t;

void udp_sensor_stream_task(void *pvParameters)
{
	udp_task_params_t *params = (udp_task_params_t *)pvParameters;
	int sock = params->sock;
	struct sockaddr_in dest_addr = params->dest_addr;
	free(params); // Free parameter struct after extracting values

	ESP_LOGI(TAG_UDP, "UDP sensor streaming task started");

	int tx_buf_size = 512;
	char *tx_buf = (char *)malloc(tx_buf_size * sizeof(char));

	// Stream sensor data at 10 Hz (100ms interval)
	const TickType_t xDelay = pdMS_TO_TICKS(100);

	while (1)
	{
		// Sample ultrasonic sensor
		int distance_cm = us_ping();

		// Get current timestamp (milliseconds since boot)
		float timestamp = (float)esp_timer_get_time() / 1000000.0; // microseconds to seconds

		// Build JSON sensor packet
		cJSON *sensor_data = cJSON_CreateObject();
		cJSON_AddStringToObject(sensor_data, "type", "proximity");
		cJSON_AddNumberToObject(sensor_data, "timestamp", timestamp);
		cJSON_AddNumberToObject(sensor_data, "distance_cm", distance_cm);
		cJSON_AddStringToObject(sensor_data, "robot_id", g_identity);

		char *json_str = cJSON_PrintUnformatted(sensor_data);

		// Send UDP packet
		int err = sendto(sock, json_str, strlen(json_str), 0,
						 (struct sockaddr *)&dest_addr, sizeof(dest_addr));
		if (err < 0)
		{
			ESP_LOGE(TAG_UDP, "Error sending UDP packet: errno %d", errno);
		}
		else
		{
			ESP_LOGD(TAG_UDP, "Sent sensor data: %s", json_str);
		}

		// Cleanup
		free(json_str);
		cJSON_Delete(sensor_data);

		// Wait for next iteration
		vTaskDelay(xDelay);
	}

	free(tx_buf);
	vTaskDelete(NULL);
}

void tcp_client(void)
{
	int addr_family = 0;
	int ip_protocol = 0;

	struct sockaddr_in dest_addr;
	inet_pton(AF_INET, g_server_host, &dest_addr.sin_addr);
	dest_addr.sin_family = AF_INET;
	dest_addr.sin_port = htons(g_server_port);
	addr_family = AF_INET;
	ip_protocol = IPPROTO_IP;

	// Create a TCP socket (IPv4).
	int sock = socket(addr_family, SOCK_STREAM, ip_protocol);
	if (sock < 0)
	{
		ESP_LOGE(TAG_TCP, "Unable to create socket: errno %d", errno);
		return;
	}
	ESP_LOGI(TAG_TCP, "Socket created, connecting to %s:%d", g_server_host, g_server_port);

	int err = connect(sock, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
	if (err != 0)
	{
		ESP_LOGE(TAG_TCP, "Socket unable to connect: errno %d", errno);
		return;
	}
	ESP_LOGI(TAG_TCP, "Successfully connected");
	// Short delay after connecting before starting register/receive loop.
	vTaskDelay(5000 / portTICK_PERIOD_MS); // delay ms

	// Attempt to register with server by first sending `g_identity` and
	// waiting for an initial server response. Then enter the receive loop
	// to process command JSON messages.
	int rx_buf_size = 1024;
	char *rx_buf = (char *)malloc(rx_buf_size * sizeof(char));
	int rx_len = 0;

	// Register identity with server and wait for an initial response.
	char registration_buf[64];
	snprintf(registration_buf, sizeof(registration_buf), "%s\n", g_identity);
	if (msg_send(sock, registration_buf, strlen(registration_buf)) != 0)
		goto CLEAN_UP;
	rx_len = msg_recv(sock, rx_buf, rx_buf_size);
	// NOTE: There is no strict validation of registration reply here.

	ESP_LOGI(TAG_TCP, "Waiting for commands");

	// ========== UDP SENSOR STREAMING SETUP ==========
	// Create UDP socket for sensor data transmission
	ESP_LOGI(TAG_UDP, "Setting up UDP socket for sensor streaming");

	struct sockaddr_in udp_dest_addr;
	udp_dest_addr.sin_addr.s_addr = dest_addr.sin_addr.s_addr; // Same server IP as TCP
	udp_dest_addr.sin_family = AF_INET;
	udp_dest_addr.sin_port = htons(DEFAULT_UDP_PORT); // UDP port 3001

	int udp_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
	if (udp_sock < 0)
	{
		ESP_LOGE(TAG_UDP, "Unable to create UDP socket: errno %d", errno);
		ESP_LOGW(TAG_UDP, "Continuing without sensor streaming");
	}
	else
	{
		ESP_LOGI(TAG_UDP, "UDP socket created for %s:%d", g_server_host, DEFAULT_UDP_PORT);

		// Prepare task parameters (will be freed by task)
		udp_task_params_t *task_params = (udp_task_params_t *)malloc(sizeof(udp_task_params_t));
		task_params->sock = udp_sock;
		task_params->dest_addr = udp_dest_addr;

		// Launch sensor streaming task on core 0 (TCP runs on core 1)
		BaseType_t task_created = xTaskCreatePinnedToCore(
			udp_sensor_stream_task, // Task function
			"UDP_Sensor_Stream",	// Task name
			4096,					// Stack size (bytes)
			(void *)task_params,	// Task parameters
			5,						// Priority (same as TCP)
			NULL,					// Task handle (not needed)
			0						// Core 0
		);

		if (task_created != pdPASS)
		{
			ESP_LOGE(TAG_UDP, "Failed to create UDP sensor streaming task");
			free(task_params);
			close(udp_sock);
		}
		else
		{
			ESP_LOGI(TAG_UDP, "UDP sensor streaming task started at 10 Hz");
		}
	}
	// ========== END UDP SETUP ==========

	// Main receive loop: get JSON commands from server, parse them, execute
	// robot actions (via motor driver functions) and send back a JSON result.
	do
	{
		rx_len = msg_recv(sock, rx_buf, rx_buf_size);
		if (rx_len > 0)
		{
			// Parse incoming JSON string into cJSON object
			cJSON *cmd = cJSON_Parse(rx_buf);
			if (cmd == NULL)
			{
				// If parsing fails, try to obtain error location and continue.
				const char *error_ptr = cJSON_GetErrorPtr();
				if (error_ptr != NULL)
				{
					ESP_LOGE(TAG_TCP, "JSON parsing error before: %s", error_ptr);
					cJSON_Delete(cmd);
					continue;
				}
			}

			// Extract numeric id field (if present) — default 0
			int id = 0;
			const cJSON *cmd_id = cJSON_GetObjectItemCaseSensitive(cmd, "id");
			if (cJSON_IsNumber(cmd_id))
			{
				id = cmd_id->valueint;
			}

			// Extract string command (e.g., "FORWARD", "PING")
			char *command = NULL;
			const cJSON *cmd_command = cJSON_GetObjectItemCaseSensitive(cmd, "command");
			if (cJSON_IsString(cmd_command) && (cmd_command->valuestring != NULL))
			{
				command = cmd_command->valuestring;
			}

			// Extract optional integer array payload (intData)
			int *iDataArray = NULL;
			int iDataArraySize = 0;
			const cJSON *cmd_intData = cJSON_GetObjectItemCaseSensitive(cmd, "intData");
			if (cJSON_IsArray(cmd_intData))
			{
				iDataArraySize = cJSON_GetArraySize(cmd_intData);
				iDataArray = (int *)malloc(iDataArraySize * sizeof(int));
				for (int i = 0; i < iDataArraySize; i++)
				{
					iDataArray[i] = cJSON_GetArrayItem(cmd_intData, i)->valueint;
				}
			}

			// Extract optional float array payload (floatData)
			float *fDataArray = NULL;
			int fDataArraySize = 0;
			const cJSON *cmd_floatData = cJSON_GetObjectItemCaseSensitive(cmd, "floatData");
			if (cJSON_IsArray(cmd_floatData))
			{
				fDataArraySize = cJSON_GetArraySize(cmd_floatData);
				fDataArray = (float *)malloc(fDataArraySize * sizeof(float));
				for (int i = 0; i < fDataArraySize; i++)
				{
					fDataArray[i] = (float)cJSON_GetArrayItem(cmd_floatData, i)->valuedouble;
				}
			}

			// Optional text payload (human-readable information)
			char *text = NULL;
			const cJSON *cmd_text = cJSON_GetObjectItemCaseSensitive(cmd, "text");
			if (cJSON_IsString(cmd_text) && (cmd_text->valuestring != NULL))
			{
				text = cmd_text->valuestring;
				if (strlen(text) > 0)
				{
					ESP_LOGI(TAG_TASK, "Received text: %s", text);
				}
			}

			// Execute the requested command and prepare result values.
			// exec_status defaults to failure and is set to success on completion.
			char *exec_status = MESSAGE_STATUS_FAILURE;
			float exec_result = 0;
			int tx_text_len = 512;
			char *tx_text = (char *)malloc(tx_text_len * sizeof(char));
			tx_text[0] = 0; // empty string
			if (command == NULL)
			{
				// Defensive handling: if server sent no command string
				ESP_LOGW(TAG_TASK, "Received NULL command from server");
				snprintf(tx_text, tx_text_len, "Received NULL command from server");
				command = "NULL";
			}
			else if (strcmp(command, "move") == 0)
			{
				// Server sends "move" with duration_seconds in float_data[0]
				// Convert to milliseconds and move forward
				ESP_LOGI(TAG_TASK, "Performing command %s", command);
				if (fDataArraySize <= 0)
				{
					snprintf(tx_text, tx_text_len, "No data received in float_data[]");
				}
				else if (fDataArray[0] <= 0)
				{
					snprintf(tx_text, tx_text_len, "Invalid duration_seconds in float_data[0]");
				}
				else
				{
					int duration_ms = (int)(fDataArray[0] * 1000.0f);
					move_forward(duration_ms);
					exec_result = fDataArray[0];
					exec_status = MESSAGE_STATUS_SUCCESS;
					snprintf(tx_text, tx_text_len, "Moved forward for %.2f seconds", fDataArray[0]);
				}
			}
			else if (strcmp(command, "turn") == 0)
			{
				// Server sends "turn" with angle_degrees in float_data[0]
				// Positive = right, negative = left
				// Rough conversion: ~90 degrees = 500ms at current motor speeds
				ESP_LOGI(TAG_TASK, "Performing command %s", command);
				if (fDataArraySize <= 0)
				{
					snprintf(tx_text, tx_text_len, "No data received in float_data[]");
				}
				else
				{
					float angle = fDataArray[0];
					int duration_ms = (int)(fabs(angle) / 90.0f * 500.0f);

					if (angle > 0)
					{
						rotate_right(duration_ms);
						snprintf(tx_text, tx_text_len, "Turned right %.1f degrees", angle);
					}
					else if (angle < 0)
					{
						rotate_left(duration_ms);
						snprintf(tx_text, tx_text_len, "Turned left %.1f degrees", fabs(angle));
					}
					else
					{
						snprintf(tx_text, tx_text_len, "Zero angle, no turn performed");
					}

					exec_result = angle;
					exec_status = MESSAGE_STATUS_SUCCESS;
				}
			}
			else if (strcmp(command, "FORWARD") == 0)
			{
				// Move forward for a duration (milliseconds) provided in
				// floatData[0]. If missing or invalid, send an error text.
				ESP_LOGI(TAG_TASK, "Performing command %s", command);
				if (fDataArraySize <= 0)
				{
					snprintf(tx_text, tx_text_len, "No data received in floatData[]");
				}
				else if (fDataArray[0] <= 0)
				{
					snprintf(tx_text, tx_text_len, "Invalid duration_ms received in floatData[0]");
				}
				else
				{
					move_forward(round(fDataArray[0]));
					// TODO: implement verification that the move completed
					exec_result = round(fDataArray[0]);
					exec_status = MESSAGE_STATUS_SUCCESS;
				}
			}
			else if (strcmp(command, "BACKWARD") == 0)
			{
				ESP_LOGI(TAG_TASK, "Performing command %s", command);
				if (fDataArraySize <= 0)
				{
					snprintf(tx_text, tx_text_len, "No data received in floatData[]");
				}
				else if (fDataArray[0] <= 0)
				{
					snprintf(tx_text, tx_text_len, "Invalid duration_ms received in floatData[0]");
				}
				else
				{
					move_backward(round(fDataArray[0]));
					exec_result = round(fDataArray[0]);
					exec_status = MESSAGE_STATUS_SUCCESS;
				}
			}
			else if (strcmp(command, "TURNLEFT") == 0)
			{
				ESP_LOGI(TAG_TASK, "Performing command %s", command);
				if (fDataArraySize <= 0)
				{
					snprintf(tx_text, tx_text_len, "No data received in floatData[]");
				}
				else if (fDataArray[0] <= 0)
				{
					snprintf(tx_text, tx_text_len, "Invalid duration_ms received in floatData[0]");
				}
				else
				{
					rotate_left(round(fDataArray[0]));
					exec_result = round(fDataArray[0]);
					exec_status = MESSAGE_STATUS_SUCCESS;
				}
			}
			else if (strcmp(command, "TURNRIGHT") == 0)
			{
				ESP_LOGI(TAG_TASK, "Performing command %s", command);
				if (fDataArraySize <= 0)
				{
					snprintf(tx_text, tx_text_len, "No data received in floatData[]");
				}
				else if (fDataArray[0] <= 0)
				{
					snprintf(tx_text, tx_text_len, "Invalid duration_ms received in floatData[0]");
				}
				else
				{
					rotate_right(round(fDataArray[0]));
					exec_result = round(fDataArray[0]);
					exec_status = MESSAGE_STATUS_SUCCESS;
				}
			}
			else if (strcmp(command, "PING") == 0)
			{
				// Perform a sonar/ultrasonic ping and return the measured value
				ESP_LOGI(TAG_TASK, "Performing command %s", command);
				exec_result = (float)us_ping();
				// TODO: add check conditions for ping success or failure
				exec_status = MESSAGE_STATUS_SUCCESS;
			}
			else
			{
				// Unknown command: log and inform server via the text field
				ESP_LOGW(TAG_TASK, "Received unrecognized command: %s", command);
				snprintf(tx_text, tx_text_len, "Received unrecognized command from server");
			}

			// Build JSON response object with id, status, result, and text.
			cJSON *res = cJSON_CreateObject();
			cJSON *res_id = cJSON_CreateNumber(id);
			cJSON *res_command = cJSON_CreateString(command);
			cJSON *res_status = cJSON_CreateString(exec_status);
			cJSON *res_intData = cJSON_CreateArray();
			cJSON *res_floatData = cJSON_CreateArray();
			cJSON *res_result = cJSON_CreateNumber(exec_result);
			cJSON *res_text = cJSON_CreateString(tx_text);
			cJSON_AddItemToObject(res, "id", res_id);
			cJSON_AddItemToObject(res, "command", res_command);
			cJSON_AddItemToObject(res, "status", res_status);
			cJSON_AddItemToObject(res, "intData", res_intData);
			cJSON_AddItemToObject(res, "floatData", res_floatData);
			cJSON_AddItemToObject(res, "result", res_result);
			cJSON_AddItemToObject(res, "text", res_text);

			// Serialize response and send back to server.
			char *json_response = cJSON_PrintUnformatted(res);
			ESP_LOGI(TAG_TCP, "Sending response: %s", json_response);
			int ret = msg_send(sock, json_response, strlen(json_response));

			// Free temporary buffers and cJSON objects.
			free(tx_text);
			cJSON_Delete(res);
			free(iDataArray);
			free(fDataArray);
			free(json_response);
			cJSON_Delete(cmd);
			if (ret != 0)
				goto CLEAN_UP;
		}
	} while (rx_len > 0);
	/* Clean up resources */
CLEAN_UP:
	free(rx_buf);
	if (sock != -1)
	{
		ESP_LOGW(TAG_TCP, "Shutting down socket...");
		shutdown(sock, 0);
		close(sock);
	}
}

/**
 * Return length if found LF, otherwise keep looping
 * Return 0 if buffer is full before finding LF
 */
int uart_read_till_lf(uart_port_t uart_num, char *rx_buf, int rx_buf_size)
{
	int len = 0;
	while (len < rx_buf_size - 1) // keep at least 1 char for terminating char '\0'
	{
		int read = uart_read_bytes(uart_num, rx_buf + len, rx_buf_size - 1 - len, MILLIS_TICKS(100));
		if (read)
		{
			len += read;
			if (rx_buf[len - 1] == '\n')
			{
				rx_buf[len] = '\0';
				return len;
			}
		}
	}
	return 0;
}

esp_err_t load_settings_from_nvs(void)
{
	nvs_handle_t nvs_handle;
	esp_err_t err;

	err = nvs_open(STORAGE_NAMESPACE, NVS_READWRITE, &nvs_handle);
	if (err != ESP_OK)
		return err;

	// g_ssid
	size_t required_size = 0;
	err = nvs_get_str(nvs_handle, "ssid", NULL, &required_size); // required size will be written in bytes, including '\0'
	if (err == ESP_ERR_NVS_NOT_FOUND)
	{
		// if not found in flash, write default to flash
		required_size = strlen(DEFAULT_SSID) + 1;
		err = nvs_set_str(nvs_handle, "ssid", DEFAULT_SSID);
		if (err != ESP_OK)
			return err;
		err = nvs_commit(nvs_handle);
		if (err != ESP_OK)
			return err;
	}
	else if (err != ESP_OK)
		return err;
	g_ssid = (char *)malloc(required_size);
	err = nvs_get_str(nvs_handle, "ssid", g_ssid, &required_size);
	if (err != ESP_OK)
		return err;
	ESP_LOGI(TAG_NVS, "Loaded ssid: %s", g_ssid);

	// g_pwd
	required_size = 0;
	err = nvs_get_str(nvs_handle, "pwd", NULL, &required_size);
	if (err == ESP_ERR_NVS_NOT_FOUND)
	{
		required_size = strlen(DEFAULT_PWD) + 1;
		err = nvs_set_str(nvs_handle, "pwd", DEFAULT_PWD);
		if (err != ESP_OK)
			return err;
		err = nvs_commit(nvs_handle);
		if (err != ESP_OK)
			return err;
	}
	else if (err != ESP_OK)
		return err;
	g_pwd = (char *)malloc(required_size);
	err = nvs_get_str(nvs_handle, "pwd", g_pwd, &required_size);
	if (err != ESP_OK)
		return err;
	ESP_LOGI(TAG_NVS, "Loaded pwd: %s", g_pwd);

	// g_server_host
	required_size = 0;
	err = nvs_get_str(nvs_handle, "server_host", NULL, &required_size);
	if (err == ESP_ERR_NVS_NOT_FOUND)
	{
		required_size = strlen(DEFAULT_SERVER_HOST) + 1;
		err = nvs_set_str(nvs_handle, "server_host", DEFAULT_SERVER_HOST);
		if (err != ESP_OK)
			return err;
		err = nvs_commit(nvs_handle);
		if (err != ESP_OK)
			return err;
	}
	else if (err != ESP_OK)
		return err;
	g_server_host = (char *)malloc(required_size);
	err = nvs_get_str(nvs_handle, "server_host", g_server_host, &required_size);
	if (err != ESP_OK)
		return err;
	ESP_LOGI(TAG_NVS, "Loaded server_host: %s", g_server_host);

	// g_server_port
	err = nvs_get_u16(nvs_handle, "server_port", &g_server_port);
	if (err == ESP_ERR_NVS_NOT_FOUND || g_server_port < 1024)
	{
		g_server_port = DEFAULT_SERVER_PORT;
		err = nvs_set_u16(nvs_handle, "server_port", DEFAULT_SERVER_PORT);
		if (err != ESP_OK)
			return err;
		err = nvs_commit(nvs_handle);
		if (err != ESP_OK)
			return err;
	}
	else if (err != ESP_OK)
		return err;
	ESP_LOGI(TAG_NVS, "Loaded server_port: %d", g_server_port);

	// g_identity
	required_size = 0;
	err = nvs_get_str(nvs_handle, "identity", NULL, &required_size);
	if (err == ESP_ERR_NVS_NOT_FOUND)
	{
		required_size = strlen(DEFAULT_IDENTITY) + 1;
		err = nvs_set_str(nvs_handle, "identity", DEFAULT_IDENTITY);
		if (err != ESP_OK)
			return err;
		err = nvs_commit(nvs_handle);
		if (err != ESP_OK)
			return err;
	}
	else if (err != ESP_OK)
		return err;
	g_identity = (char *)malloc(required_size);
	err = nvs_get_str(nvs_handle, "identity", g_identity, &required_size);
	if (err != ESP_OK)
		return err;
	ESP_LOGI(TAG_NVS, "Loaded identity: %s", g_identity);

	return ESP_OK;
}

void app_main(void)
{
	// initialize robot hardware
	ESP_LOGI(TAG_DRIVER, "Initializing pins");
	pin_config();
	ESP_LOGI(TAG_DRIVER, "Pins initialized");
	// start LED test pin
	// xTaskCreatePinnedToCore(task_blink_led, "LED Thread", 4096, NULL, 5, NULL, 1);

	// JSON test
	cJSON *myJson = cJSON_Parse(MSG_TEST_1);
	char *myJsonString = cJSON_Print(myJson);
	ESP_LOGI(TAG_0, "JSON: %s", myJsonString);
	free(myJsonString);
	cJSON_Delete(myJson);

	// Initialize NVS
	esp_err_t ret = nvs_flash_init();
	if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND)
	{
		ESP_ERROR_CHECK(nvs_flash_erase());
		ret = nvs_flash_init();
	}
	ESP_ERROR_CHECK(ret);

	// UART configuration
	ESP_LOGI(TAG_UART, "Initializing UART");
	int rx_buf_size = 1024;
	int tx_buf_size = 1024;
	char *rx_buf = (char *)malloc(rx_buf_size);
	char *tx_buf = (char *)malloc(tx_buf_size);
	uart_config_t uart_config = {
		.baud_rate = 115200,
		.data_bits = UART_DATA_8_BITS,
		.parity = UART_PARITY_DISABLE,
		.stop_bits = UART_STOP_BITS_1,
		.flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
		.source_clk = UART_SCLK_DEFAULT,
	};
	int intr_alloc_flags = 0;
#if CONFIG_UART_ISR_IN_IRAM
	intr_alloc_flags = ESP_INTR_FLAG_IRAM;
#endif
	ESP_ERROR_CHECK(uart_driver_install(UART_NUM_0, rx_buf_size, tx_buf_size, 0, NULL, intr_alloc_flags));
	ESP_ERROR_CHECK(uart_param_config(UART_NUM_0, &uart_config));
	ESP_ERROR_CHECK(uart_set_pin(UART_NUM_0, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));

	// UART communication
	uart_flush_input(UART_NUM_0);
	ESP_LOGI(TAG_UART, "Requesting to configure");
	snprintf(tx_buf, tx_buf_size, "%s request to configure robot\r\n", UART_MAGIC_ROBOT);
	uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
	uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
	// Wait for SerialTool to respond within timeout period
	int configure = 0;
	int read = uart_read_bytes(UART_NUM_0, rx_buf, rx_buf_size, MILLIS_TICKS(1000));
	if (read)
	{
		rx_buf[read] = '\0';
		ESP_LOGI(TAG_UART, "Received: %s", rx_buf);
		if (strstr(rx_buf, UART_MAGIC_TOOL))
		{
			configure = 1;
			snprintf(tx_buf, tx_buf_size, "%s Established connection with SerialTool\r\n", UART_MAGIC_ROBOT);
			uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
			uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
		}
	}
	if (configure)
	{
		nvs_handle_t nvs_handle;
		esp_err_t err;
		err = nvs_open(STORAGE_NAMESPACE, NVS_READWRITE, &nvs_handle);

		while (err == ESP_OK)
		{
			uart_read_till_lf(UART_NUM_0, rx_buf, rx_buf_size);
			ESP_LOGI(TAG_UART, "Received: %s", rx_buf);
			char *substr = strstr(rx_buf, UART_MAGIC_TOOL);
			if (!substr)
				continue;
			// parse command
			char *command = strstr(substr, "reset");
			if (command)
			{
				err = nvs_erase_all(nvs_handle);
				snprintf(tx_buf, tx_buf_size, "%s resetting flash to default values\r\n", UART_MAGIC_ROBOT);
				uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
				uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
				continue;
			}
			command = strstr(substr, "done configuration");
			if (command)
			{
				snprintf(tx_buf, tx_buf_size, "%s exiting configuration state\r\n", UART_MAGIC_ROBOT);
				uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
				uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
				break;
			}
			command = strstr(substr, "set ssid ");
			if (command)
			{
				if (strlen(command) <= strlen("set ssid "))
				{
					snprintf(tx_buf, tx_buf_size, "%s ssid too short\r\n", UART_MAGIC_ROBOT);
					uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
					uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
					continue;
				}
				command += strlen("set ssid ");
				command[strcspn(command, "\r\n")] = 0; // remove trailing CRLF
				err = nvs_set_str(nvs_handle, "ssid", command);
				err = nvs_commit(nvs_handle);
				snprintf(tx_buf, tx_buf_size, "%s setting ssid to: %s\r\n", UART_MAGIC_ROBOT, command);
				uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
				uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
				continue;
			}
			command = strstr(substr, "set pwd ");
			if (command)
			{
				if (strlen(command) <= strlen("set pwd "))
				{
					snprintf(tx_buf, tx_buf_size, "%s pwd too short\r\n", UART_MAGIC_ROBOT);
					uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
					uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
					continue;
				}
				command += strlen("set pwd ");
				command[strcspn(command, "\r\n")] = 0; // remove trailing CRLF
				err = nvs_set_str(nvs_handle, "pwd", command);
				err = nvs_commit(nvs_handle);
				snprintf(tx_buf, tx_buf_size, "%s setting pwd to: %s\r\n", UART_MAGIC_ROBOT, command);
				uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
				uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
				continue;
			}
			command = strstr(substr, "set server_host ");
			if (command)
			{
				if (strlen(command) <= strlen("set server_host "))
				{
					snprintf(tx_buf, tx_buf_size, "%s server_host too short\r\n", UART_MAGIC_ROBOT);
					uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
					uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
					continue;
				}
				command += strlen("set server_host ");
				command[strcspn(command, "\r\n")] = 0; // remove trailing CRLF
				err = nvs_set_str(nvs_handle, "server_host", command);
				err = nvs_commit(nvs_handle);
				snprintf(tx_buf, tx_buf_size, "%s setting server_host to: %s\r\n", UART_MAGIC_ROBOT, command);
				uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
				uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
				continue;
			}
			command = strstr(substr, "set server_port ");
			if (command)
			{
				if (strlen(command) <= strlen("set server_port "))
				{
					snprintf(tx_buf, tx_buf_size, "%s server_port too short\r\n", UART_MAGIC_ROBOT);
					uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
					uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
					continue;
				}
				command += strlen("set server_port ");
				command[strcspn(command, "\r\n")] = 0; // remove trailing CRLF
				uint16_t port = (uint16_t)strtol(command, (char **)NULL, 10);
				err = nvs_set_u16(nvs_handle, "server_port", port);
				err = nvs_commit(nvs_handle);
				snprintf(tx_buf, tx_buf_size, "%s setting server_port to: %d\r\n", UART_MAGIC_ROBOT, port);
				uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
				uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
				continue;
			}
			command = strstr(substr, "set identity ");
			if (command)
			{
				if (strlen(command) <= strlen("set identity "))
				{
					snprintf(tx_buf, tx_buf_size, "%s identity too short\r\n", UART_MAGIC_ROBOT);
					uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
					uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
					continue;
				}
				command += strlen("set identity ");
				command[strcspn(command, "\r\n")] = 0; // remove trailing CRLF
				err = nvs_set_str(nvs_handle, "identity", command);
				err = nvs_commit(nvs_handle);
				snprintf(tx_buf, tx_buf_size, "%s setting identity to: %s\r\n", UART_MAGIC_ROBOT, command);
				uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
				uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
				continue;
			}

			snprintf(tx_buf, tx_buf_size, "%s unknown command: %s\r\n", UART_MAGIC_ROBOT, substr + strlen(UART_MAGIC_TOOL));
			uart_write_bytes(UART_NUM_0, tx_buf, strlen(tx_buf));
			uart_wait_tx_done(UART_NUM_0, MILLIS_TICKS(1000));
		}

		if (err != ESP_OK)
			ESP_LOGE(TAG_NVS, "NVS failed with code: %d", err);
		nvs_close(nvs_handle);
	}
	free(rx_buf);
	free(tx_buf);
	ESP_LOGI(TAG_UART, "Done configuring");

	// load configuration from NVS
	esp_err_t err = load_settings_from_nvs();
	if (err != ESP_OK)
	{
		ESP_LOGE(TAG_NVS, "Failed to load from NVS. Error code: %d. Using hardcoded defaults", err);
		g_ssid = (char *)malloc(strlen(DEFAULT_SSID) + 1);
		g_pwd = (char *)malloc(strlen(DEFAULT_PWD) + 1);
		g_server_host = (char *)malloc(strlen(DEFAULT_SERVER_HOST) + 1);
		g_identity = (char *)malloc(strlen(DEFAULT_IDENTITY) + 1);
		strcpy(g_ssid, DEFAULT_SSID);
		strcpy(g_pwd, DEFAULT_PWD);
		strcpy(g_server_host, DEFAULT_SERVER_HOST);
		g_server_port = DEFAULT_SERVER_PORT;
		strcpy(g_identity, DEFAULT_IDENTITY);
	}

	// start wireless operation
	ESP_LOGI(TAG_WIFI, "Start WiFi scan");
	fast_scan();

	// Keep app_main alive so event loop can process WiFi events
	// The TCP client will run in the event handler once IP is obtained
	while (1)
	{
		vTaskDelay(pdMS_TO_TICKS(1000));
	}
}
