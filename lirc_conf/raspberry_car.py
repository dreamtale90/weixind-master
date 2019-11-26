# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import time
import sys

# BOARD编号方式，基于插座引脚编号
GPIO.setmode(GPIO.BCM)

# 输出模式
GPIO.setup(17, GPIO.OUT)
GPIO.setup(27, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(24, GPIO.OUT)

def Forward(time_s):
    GPIO.output(17, GPIO.HIGH)
    GPIO.output(27, GPIO.LOW)
    GPIO.output(23, GPIO.HIGH)
    GPIO.output(24, GPIO.LOW)
    time.sleep(time_s)

def Backward(time_s):
    GPIO.output(17, GPIO.LOW)
    GPIO.output(27, GPIO.HIGH)
    GPIO.output(23, GPIO.LOW)
    GPIO.output(24, GPIO.HIGH)
    time.sleep(time_s)

def TurnLeft(time_s):
    GPIO.output(17, GPIO.LOW)
    GPIO.output(27, GPIO.HIGH)
    GPIO.output(23, GPIO.HIGH)
    GPIO.output(24, GPIO.LOW)
    time.sleep(time_s)

def TurnRight(time_s):
    GPIO.output(17, GPIO.HIGH)
    GPIO.output(27, GPIO.LOW)
    GPIO.output(23, GPIO.LOW)
    GPIO.output(24, GPIO.HIGH)
    time.sleep(time_s)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Too few arguments !"
        sys.exit()

    if sys.argv[1] == "Forward":
        print "forward"
        Forward(2)
    elif sys.argv[1] == "Backward":
        print "backward"
        Backward(2)
    elif sys.argv[1] == "TurnLeft":
        print "left"
        TurnLeft(0.22)
    elif sys.argv[1] == "TurnRight":
        print "right"
        TurnRight(0.22)
    else:
        print "Invalid argument !"
        print sys.argv[1]

    GPIO.cleanup()

