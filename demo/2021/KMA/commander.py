from indy_utils.indy_shm import *
from indy_utils import indyeye_client as eye

import json
from time import sleep
import time
import threading
import numpy as np
import signal, sys, os

indy_master = IndyShmCommand()
indy_master.set_sync_mode(True)

eye_ip = '192.168.137.100'
indy_eye = eye.IndyEyeClient(eye_ip)

COMMAND_ADDR = 800

agv_1_pos = [
    [0.073, -0.248, -0.20, 90.052, -4.983, 178.181], # holder 1
    [0.068, -0.138, -0.20, 90.118, -4.921, 178.308], # holder 2
    [0.064, -0.028, -0.20, 90.005, -4.899, 178.329] # holder 3
]

agv_2_pos = [
    [0.062, -0.252, -0.196, 90.0, -1.0, 178.2], # holder 1
    [0.062, -0.144, -0.196, 90.0, -1.0, 178.213], # holder 2
    [0.061, -0.033, -0.196, 90.0, -1.0, 178.263], # holder 3
]

def wait_for_motion_finish():
    while indy_master.get_robot_status()['busy']:
        sleep(0.05)

def reset_cmd():
    sleep(0.01)
    indy_master.write_direct_variable(0, COMMAND_ADDR, 0)

def agv_place(marker, pos):
    indy_master.set_reference_frame(marker)
    pre_place_pos = [p for p in pos]
    pre_place_pos[2] = pre_place_pos[2] + 0.05

    indy_master.task_move_to(pre_place_pos)
    wait_for_motion_finish()
    indy_master.task_move_to(pos)
    wait_for_motion_finish()

def agv_place_post(marker, pos):
    indy_master.set_reference_frame(marker)
    post_place_pos = [p for p in pos]
    post_place_pos[1] = post_place_pos[1] - 0.1

    indy_master.task_move_to(post_place_pos)
    wait_for_motion_finish()

def main():
    marker = None
#     marker = [-0.03638189059012668,
#  0.8722079642528565,
#  0.42202856199738364,
#  -0.7919939124199473,
#  -4.575374507532725,
#  -1.1852250583854933]

    while True:
        time.sleep(0.02)

        cmd = indy_master.read_direct_variable(0, COMMAND_ADDR)

        if cmd == 1:
            wait_for_motion_finish()

            cnt = 0
            while True:
                time.sleep(0.5)
                indy_master.set_reference_frame([0, 0, 0, 0, 0, 0])
                marker  = indy_eye.detect(1, indy_master.get_task_pos(), 'Tbo')
                if marker:
                    indy_master.set_reference_frame(marker)
                    indy_master.task_move_to([0.008, -0.229, 0.143, 0, 147.729, 91.022])
                    wait_for_motion_finish()
                    cnt = cnt + 1
                else:
                    cnt = 0

                if cnt > 2:
                    break
                
            reset_cmd()

        if cmd == 2:
            wait_for_motion_finish()
            indy_master.set_reference_frame([0, 0, 0, 0, 0, 0])
            reset_cmd()

        for i in range(1, 4):
            if cmd == i+10: # agv 1 holder place
                wait_for_motion_finish()
                if marker:
                    agv_place(marker, agv_1_pos[i-1])
                    reset_cmd()
                else:
                    break

            if cmd == i+20: # agv 2 holder place
                wait_for_motion_finish()
                if marker:
                    agv_place(marker, agv_2_pos[i-1])
                    reset_cmd()
                else:
                    break

            if cmd == i+100: # agv 1 holder place post
                wait_for_motion_finish()
                if marker:
                    agv_place_post(marker, agv_1_pos[i-1])
                    reset_cmd()
                else:
                    break

            if cmd == i+200: # agv 2 holder place post
                wait_for_motion_finish()
                if marker:
                    agv_place_post(marker, agv_2_pos[i-1])
                    reset_cmd()
                else:
                    break


def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    sys.exit(-1)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    os.system("taskset -p -c 0,1 %d" % os.getpid())

    main()

        