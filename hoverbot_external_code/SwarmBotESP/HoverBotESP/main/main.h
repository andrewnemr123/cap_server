#ifndef MAIN_MAIN_H_
#define MAIN_MAIN_H_

// includes
#include <esp_log.h>

// logging tags
#define TAG_0 "Main Thread"
#define TAG_UART "UART"
#define TAG_NVS "NVS"
#define TAG_WIFI "WIFI"
#define TAG_TCP "TCP"
#define TAG_UDP "UDP"
#define TAG_TASK "TASK"
#define TAG_DRIVER "DRIVER"

// keywords for UART substring detection, must be the same as SerialTool
#define UART_MAGIC_TOOL "UART_MAGIC_TOOL;"
#define UART_MAGIC_ROBOT "UART_MAGIC_ROBOT;"

// NVS
#define STORAGE_NAMESPACE "swarmbot"

// wifi defaults
#define DEFAULT_SSID "AndrewiPhone"
#define DEFAULT_PWD "andypass"
#define DEFAULT_SERVER_HOST "172.20.10.2" // Patrick laptop
#define DEFAULT_SERVER_PORT 3000
#define DEFAULT_SCAN_METHOD WIFI_FAST_SCAN
#define DEFAULT_SORT_METHOD WIFI_CONNECT_AP_BY_SIGNAL
#define DEFAULT_RSSI -127
#define DEFAULT_AUTHMODE WIFI_AUTH_OPEN

// server
#define DEFAULT_IDENTITY "HOVERBOT"
#define DEFAULT_UDP_PORT 3001
#define MESSAGE_STATUS_SUCCESS "SUCCESS"
#define MESSAGE_STATUS_FAILURE "FAILURE"

// macro
#define MILLIS_TICKS(x) (x / portTICK_PERIOD_MS) // convert x milliseconds to RTOS ticks

// globals
extern char *g_ssid;
extern char *g_pwd;
extern char *g_server_host;
extern uint16_t g_server_port;
extern char *g_identity;

#endif /* MAIN_MAIN_H_ */
