"""USB serial configuration tool for SwarmBots using the ESP32 framework.

Usage:
    Normal mode:     python main.py [--port COM3]
    Monitor mode:    python main.py -m [--port COM3]
    Debug mode:      python main.py -d [--port COM3]
    Help:            python main.py -h

See README.md for detailed documentation.
"""


import argparse
import logging
import sys

import serial
from serial.tools.list_ports import comports
from serial.tools.miniterm import Miniterm

# constants
TIMEOUT_SERIAL_SECONDS = 5
# keywords for UART substring detection, must be the same as microcontrollers
UART_MAGIC_TOOL = b'UART_MAGIC_TOOL;'
UART_MAGIC_ROBOT = b'UART_MAGIC_ROBOT;'


def wait_for_expected_response(expected: bytes) -> bytes:
    """
    Wait for a line that contains the expected message subsequence.
    Return bytes where the part before the subsequence is removed.
    """
    while True:
        res = board.read_until()  # read until LF
        logging.debug(f"Response: {res}")
        index = res.find(expected)
        if index != -1:
            logging.debug(f"Found subsequence {expected} at index {index}")
            return res[index:]


def ask_for_port():
    """
    Show a list of ports and ask the user for a choice.
    """
    sys.stderr.write('\n--- Available ports:\n')
    ports = []
    for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
        sys.stderr.write('--- {:2}: {:20} {!r}\n'.format(n, port, desc))
        ports.append(port)
    while True:
        port = input('--- Enter port index or full name: ')
        try:
            index = int(port) - 1
            if not 0 <= index < len(ports):
                sys.stderr.write('--- Invalid index!\n')
                continue
        except ValueError:
            pass
        else:
            port = ports[index]
        return port


def connect(port: str, baudrate: int, timeout: float) -> serial.Serial:
    """
    Connect to a serial port.

    :param port: serial port name
    :param baudrate: baudrate of the connection
    :param timeout: read timeout in seconds
    :return: the opened serial object
    """
    ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
    if ser.is_open:
        logging.info(f"Connected to {ser.port}")
    else:
        logging.error(f"Failed to connect to {ser.port}")
    return ser


def key_description(character):
    """generate a readable description for a key"""
    ascii_code = ord(character)
    if ascii_code < 32:
        return 'Ctrl+{:c}'.format(ord('@') + ascii_code)
    else:
        return repr(character)


if __name__ == '__main__':
    # set up log to console
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    # parse arguments (use -h or --help to see help messages)
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", nargs=1, required=False, help="specify outgoing serial port name (e.g. COM3)")
    parser.add_argument("--baudrate", nargs=1, type=int, default=[115200], help="specify baudrate (default: 115200)")
    parser.add_argument("-m", "--monitor", action="store_true", help="will act as serial monitor if set")
    parser.add_argument("-d", "--debug", action="store_true", help="will enable debug messages if set")
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.info("Enabled debug mode")
    if args.monitor:
        logging.info("Enabled monitor mode")

    serial_port = None
    if args.port is not None:
        serial_port = args.port[0]
    else:
        serial_port = ask_for_port()
    logging.info(f"Using serial port {serial_port}")

    serial_baudrate = args.baudrate[0]
    logging.info(f"Using baudrate {serial_baudrate}")

    # monitor mode
    if args.monitor:
        try:
            serial_instance = serial.serial_for_url(serial_port, serial_baudrate, parity="N", rtscts=False,
                                                    xonxoff=False, do_not_open=True)
            serial_instance.open()
        except serial.SerialException as e:
            logging.error(f"Could not open port {serial_port}: {e}")
            sys.exit(1)
        miniterm = Miniterm(serial_instance, filters=("direct",))
        miniterm.exit_character = chr(0x1d)  # CTRL + ]
        miniterm.menu_character = chr(0x14)  # CTRL + T
        miniterm.raw = False
        miniterm.set_rx_encoding("UTF-8")
        miniterm.set_tx_encoding("UTF-8")
        sys.stderr.write('--- Miniterm on {p.name}  {p.baudrate},{p.bytesize},{p.parity},{p.stopbits} ---\n'.format(
            p=miniterm.serial))
        sys.stderr.write('--- Quit: {} | Menu: {} | Help: {} followed by {} ---\n'.format(
            key_description(miniterm.exit_character),
            key_description(miniterm.menu_character),
            key_description(miniterm.menu_character),
            key_description('\x08')))
        miniterm.start()
        try:
            miniterm.join(True)
        except KeyboardInterrupt:
            pass
        sys.stderr.write('\n--- exit ---\n')
        miniterm.join()
        miniterm.close()
        sys.exit(0)

    # normal mode (configure)
    board = connect(serial_port, serial_baudrate, TIMEOUT_SERIAL_SECONDS)
    board.reset_input_buffer()
    board.reset_output_buffer()

    # Release both lines so IO0 stays high and EN stays high (no bootloader)
    # Then press EN manually once you see the log below.
    board.setDTR(False)   # IO0 released (high)
    board.setRTS(False)   # EN released (high)
    logging.info("Reboot the board. Waiting for configure request")
    clean_res = wait_for_expected_response(UART_MAGIC_ROBOT)
    logging.info(f"Tool Received: {clean_res}")
    to_send = b' '.join([UART_MAGIC_TOOL, b'acknowledged\r\n'])
    logging.info(f"Tool Sending: {to_send}")
    board.write(to_send)
    # configure
    clean_res = wait_for_expected_response(UART_MAGIC_ROBOT)
    logging.info(f"Tool Received: {clean_res}")
    while True:
        user_in = input("Command to send: ")
        user_in += "\r\n"
        to_send = b' '.join([UART_MAGIC_TOOL, user_in.encode(encoding="utf-8")])
        logging.info(f"Tool Sending: {to_send}")
        board.write(to_send)
        clean_res = wait_for_expected_response(UART_MAGIC_ROBOT)
        logging.info(f"Tool Received: {clean_res}")
        if user_in == "done configuration\r\n":
            break

    # end
    board.close()
    logging.info("Closed serial connection")
