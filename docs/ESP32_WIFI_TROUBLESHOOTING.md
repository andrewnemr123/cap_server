# ESP32 WiFi Connection Troubleshooting

## Current Issue

Your ESP32 HOVERBOT is cycling through connection states:
```
init -> auth -> assoc -> run -> init (timeout after 10s)
```

This indicates authentication succeeds but the connection drops before completing.

---

## Solutions (Try in Order)

### 1. **Verify iPhone Hotspot Settings**

On your iPhone:
- Settings → Personal Hotspot
- Turn OFF "Maximize Compatibility" (try WPA3 first)
- If that fails, turn ON "Maximize Compatibility" (forces WPA2)
- Note the EXACT password (case-sensitive)
- Ensure "Allow Others to Join" is enabled

### 2. **Update ESP32 WiFi Credentials**

Your ESP32 has these stored:
```
SSID: AndrewiPhone
Password: andypass
Server: 172.20.10.2:3000
```

**To reconfigure via serial console:**

Send this command over UART:
```
UART_MAGIC_ROBOT
```

Then follow prompts to re-enter WiFi credentials.

### 3. **Check iPhone IP Address**

Your ESP32 is trying to connect to `172.20.10.2`. Verify your iPhone hotspot uses this subnet:

- iPhone Settings → Personal Hotspot → tap the (i) icon
- Check if IP is in `172.20.10.x` range
- If different, update ESP32 server_host in NVS

### 4. **Increase WiFi Timeout (ESP32 Code)**

In your ESP32 firmware, increase connection timeout:

```c
// In wifi component
esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
esp_wifi_connect();

// Wait longer for connection
vTaskDelay(pdMS_TO_TICKS(15000)); // Increase from 10s to 15s
```

### 5. **Add DHCP Debugging**

The ESP32 reaches "run" state but might be failing DHCP. Add this to your ESP32 code:

```c
#include "esp_netif.h"

// After wifi_init
esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");

// In event handler
case IP_EVENT_STA_GOT_IP: {
    ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
    ESP_LOGI(TAG, "Got IP:" IPSTR, IP2STR(&event->ip_info.ip));
    // Signal connection success here
    break;
}
```

### 6. **Try Static IP (Bypass DHCP)**

If DHCP is failing, configure static IP on ESP32:

```c
esp_netif_dhcpc_stop(netif);
esp_netif_ip_info_t ip_info = {
    .ip = { .addr = ESP_IP4TOADDR(172, 20, 10, 4) },
    .gw = { .addr = ESP_IP4TOADDR(172, 20, 10, 1) },
    .netmask = { .addr = ESP_IP4TOADDR(255, 255, 255, 0) }
};
esp_netif_set_ip_info(netif, &ip_info);
```

---

## Diagnostic Commands

**Check server logs:**
```bash
# On your Mac
python3 -m src.llm.server
# Look for connection from 172.20.10.x
```

**Monitor ESP32 serial output:**
```bash
# Look for these success indicators:
# - "wifi:state: run -> run"  (stable connection)
# - "IP_EVENT_STA_GOT_IP"     (DHCP success)
# - "TCP: Connected to server" (your app connected)
```

---

## Quick Test

**Simplest fix to try NOW:**

1. **Turn iPhone hotspot OFF then ON** (resets DHCP pool)
2. **Restart ESP32** (power cycle)
3. **Wait 30 seconds** for full connection
4. **Check server logs** for connection from ESP32

If still failing, the issue is likely:
- Wrong password in ESP32 NVS
- WPA2/WPA3 incompatibility
- DHCP timeout

---

## Expected Working Output

When successful, you should see:

```
I (xxxx) wifi:state: assoc -> run (0x10)
I (xxxx) wifi:<ba-add>idx:0 (ifx:0, xx:xx:xx:xx:xx:xx), tid:0, ssn:0, winSize:64
I (xxxx) IP_EVENT_STA_GOT_IP: IP:172.20.10.4, MASK:255.255.255.0, GW:172.20.10.1
I (xxxx) TCP: Connecting to 172.20.10.2:3000
I (xxxx) TCP: Connected to server
I (xxxx) TCP: Sent registration: {"command":"register","bot":"HOVERBOT"}
```

Then on the server you'll see:
```
✅ Connection from ('172.20.10.4', 53493)
✅ [REGISTRATION] Client ('172.20.10.4', 53493) registered as HOVERBOT
```
