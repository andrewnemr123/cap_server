# SwarmBotESP

## Setting up development environment with ESP32

1. Download and install USB-UART bridge drivers from [CP210x USB to UART Bridge VCP Drivers](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers?tab=downloads)
    - Follow instructions in the release notes to install (on Windows, right click on `silabser.inf` file and click "Install")
    - It is possible that your model of the board uses a different USB-to-UART bridge than HoverBotESP. In that case, follow the detailed instruction from [Establish Serial Connection with ESP32](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/establish-serial-connection.html)
2. (Recommended for Windows) Download and install Espressif-IDE from [ESP-IDF Windows Installer Download](https://dl.espressif.com/dl/esp-idf/)
    - The IDE has a bug where the C Indexer would stop working sometimes, making a lot of errors appear in the text editor (but still compiles). To avoid this bug, **close the project before closing the IDE** and reopen the project when you start the IDE, then build the project. (Note: for any newly created or imported projects, you need to build the project first before the indexer starts to work)
    - For Mac and Linux, and Windows if you do not want to use the Espressif-IDE, follow instructions from [Getting Started with ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/get-started/index.html)

    **It's highly recommended that you follow through [Getting Started with ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/get-started/index.html) either way and experiment yourself with a new project before start working on the existing SwarmBotESP projects.**

3. Import or create a new project by selecting "Espressif IDF Project"
4. Finding the COM port on windows:
    - Go to This PC/Manage and find CP210 under USB/COM ports
    - Alternatively, select it from the drop down menu in Espressif-IDE's build target selection
5. When flashing (i.e. uploading code) to the board, if the board refuses to connect, then the board is in the wrong boot mode. To force the board into the correct boot mode:
    - When flashing, once the terminal displays "connecting", hold the "Boot" button on the board

## Using SerialTool to monitor the robot

Read the comments at the top of the `main.py` file in the SerialTool folder on how to use SerialTool. Once SerialTool is set up, run the command `py main.py -m` to enter Serial Monitor Mode. The board needs to be connected to the computer via USB.

## Using SerialTool to configure the robot

The following commands are currently valid to be sent by the SerialTool to the ESP32

1. `reset`: reset values stored in flash to default hardcoded ones
2. `done configuration`: make the ESP32 exit the configuration state
3. `set ssid SSID_NAME`: replace SSID_NAME with the SSID of the WiFi network the board is supposed to try to connect to
4. `set pwd PWD`: replace PWD with the password of the WiFi network
5. `set server_host SERVER_HOST`: replace SERVER_HOST with the IPv4 address of the computer on which TcpServer is running (e.g. `set server_host 192.168.1.139`)
6. `set server_port SERVER_PORT`: replace SERVER_PORT with the port that the server is listening to
7. `set identity IDENTITY`: replace IDENTITY with the identity (name) of the robot (e.g. `set identity HOVERBOT`)

## Future Improvements

1. Move the TCP communication with the server to a dedicated FreeRTOS task so it doesn't block other operations of the robot such as controlling the motors or getting data from the sensors. Alternatively, create new tasks to perform those operations. FreeRTOS is already enabled and tasks can be created with `xTaskCreate()` or `xTaskCreatePinnedToCore()` (since there are two cores on the ESP32)
    - Implement the possibility of sending an "Emergency Stop" message **while** the robot is executing a task. For example, if a command of moving forward too much is sent by accident, we would like to be able to abort the command
    - If a command that takes a long time to complete is sent, we would like to know that the robot has indeed at least received the command and is currently executing it
    - Source code of the TcpServer will also need to be updated to implement these new changes

2. Support storing multiple SSIDs and scan them by priorities or by signal strength
3. Support automatic discovery of `server_host` once connected to a WiFi network
