from indy_utils import indydcp_client as client
from datetime import datetime

import json
from time import sleep
import threading
import numpy as np
# Master robot

robot_ip = "127.0.0.1"  # Robot (Indy) IP
robot_name = "NRMK-Indy7"  # Robot name (Indy7)

indy = client.IndyDCPClient(robot_ip, robot_name)

def set_gripper_mode(indy, mode):
    indy.set_endtool_do(0, mode)

def set_gripper_cmd(indy, cmd):
    indy.set_endtool_do(1, cmd)

indy.connect()

set_gripper_mode(indy, 32)
sleep(3)
set_gripper_cmd(indy, 0)
sleep(3)
set_gripper_mode(indy, 16)
sleep(3)
set_gripper_cmd(indy, 5)
sleep(3)
set_gripper_mode(indy, 32)
sleep(3)
set_gripper_cmd(indy, 1)
sleep(3)
set_gripper_mode(indy, 48)

indy.disconnect()