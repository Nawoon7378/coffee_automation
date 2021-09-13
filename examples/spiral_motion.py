from indy_utils import indydcp_client as client

import json
from time import sleep
import threading
import numpy as np

center_offset = [0.01, 0, 0, 0, 0, 0]
direction = [0, 0.05, 0, 0, 0, 0]
angle = 3.141692 * 100

robot_ip = "127.0.0.1"  # Robot (Indy) IP
robot_name = "NRMK-Indy7"  # Robot name (Indy7)

indy = client.IndyDCPClient(robot_ip, robot_name)

def timer():
    sleep(5)
    client.GLOBAL_DICT['stop'] = True
    
th = threading.Thread(target=timer)
th.start()

indy.connect()
indy.set_sync_mode(True)
indy.set_reduced_mode(True)
indy.set_reduced_speed_ratio(0.15)

p0 = indy.get_task_pos()
p1 = [p0[i] + center_offset[i] for i in range(6)]
p2 = [p0[i] + direction[i] for i in range(6)]

indy.task_spiral_move(p1, p2, angle)

indy.set_reduced_mode(False)
indy.disconnect()
