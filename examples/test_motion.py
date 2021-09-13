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
indy.connect()

while True:
    sleep(5)
    with open('foo.txt', 'a') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S\n'))

    indy.joint_move_to([0, -20, -90, 0, -60, 0])
    sleep(5)
    indy.joint_move_to([10, -20, -90, 0, -60, 0])


indy.disconnect()

