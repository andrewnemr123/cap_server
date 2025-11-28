# Hover Robot Program ~ MODBUS TCP/IP Ethernet Cable Connection

# LIBRARIES

import socket
import time
import sys
import errno
import ctypes

# Give the IP address of the robot and control it from here directly
# CLASS

def hover(hoverRobot):

#CONNECTION
     
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print ('failed to create socket connection to the hover robot')
        
    s.connect((hoverRobot, 502))
    print ('Socket created successfully for the hover robot')
   

#FUNCTIONS
    
def move(Direction): # 1 = Forward, 2 = Backward, 3 = Left, 4 = Right
    direction = Direction
    if direction == 1:
        moveForward(speed)
    if direction == 2:
        moveBackward(speed)
    if direction == 3:
        moveLeft(speed)
    if direction == 4:
        moveRight(speed)
        
def takePicture():
    # code to take picture

def recognizeFace(picture):
    # code to recognize face

#ACTION
hover("192.168.0.4")
