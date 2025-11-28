# Hover Robot Program ~ MODBUS TCP/IP Ethernet Cable Connection

# LIBRARIES

import socket
import time
import sys
import errno
import ctypes
import can
import canopen

# Give the IP address of the robot and control it from here directly

# CLASS

def hover():

#CONNECTION
     
    try:
        robotNetwork = canopen.Network()
        robotNetwork.connect(channel='/dev/ttyS1', bustype='serial')
        hoverRobot1 = robotNetwork.add_node(1, 'hoverRobotObjectDictionary.eds')
        hoverRobot2 = robotNetwork.add_node(2, 'hoverRobotObjectDictionary.eds')
        hoverRobot3 = robotNetwork.add_node(3, 'hoverRobotObjectDictionary.eds')
        hoverRobot4 = robotNetwork.add_node(4, 'hoverRobotObjectDictionary.eds')
        hoverRobot5 = robotNetwork.add_node(5, 'hoverRobotObjectDictionary.eds')
        robotNetwork.add_node(hoverRobot1)
        robotNetwork.add_node(hoverRobot2)
        robotNetwork.add_node(hoverRobot3)
        robotNetwork.add_node(hoverRobot4)
        robotNetwork.add_node(hoverRobot5)
        robotNetwork.disconnect()
        
    except can.exception:
        print ('Exception: check hardware is connected correctly')
        
#FUNCTIONS
    
def move(node, Direction): # 1 = Forward, 2 = Backward, 3 = Left, 4 = Right
    direction = Direction
    if direction == 1:
        node.pdo[].raw = forward()
    if direction == 2:
        node.pdo[].raw = backward()
    if direction == 3:
        node.pdo[].raw = left())
    if direction == 4:
        node.pdo[].raw = right()
        
def takePicture():
    # code to take picture

def recognizeFace(picture):
    # code to recognize face

#ACTION
hover()
