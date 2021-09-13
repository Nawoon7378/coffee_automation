from indy_utils.indy_shm import *
import time

import json
from time import sleep
import signal, sys
import threading
import numpy as np

indy_master = IndyShmCommand()
tic = {}
COMMANDER_ADDR = 600

def wait_for_motion_finish():
    while indy_master.get_robot_status()['busy']:
        pass

def reset_cmd():
    sleep(0.05)
    indy_master.write_direct_variable(0, COMMANDER_ADDR, 0)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    indy_master.stop_jog()
    sys.exit(-1)

def main():
    prev_task_pos = indy_master.get_task_pos()
    indy_master.write_direct_variable(0, COMMANDER_ADDR, 0)
    while True:
        cmd = indy_master.read_direct_variable(0, COMMANDER_ADDR)

        if cmd == 1:
            wait_for_motion_finish()

            target = [p for p in prev_task_pos]
            target[2] = target[2] + 0.02
            indy_master.set_task_vel_level(5)
            indy_master.task_move_to(target)

            wait_for_motion_finish()

            tic[0] = time.time()

            while True:
                tic[1] = time.time()
                indy_master.task_jog_move(1,0,0,1,0,0,0,1) # v, xyzuvw, base
                tic[2] = time.time()
                sleep(0.05)

                # print('task time', tic[2] - tic[1])
                # print('entire time', tic[2] - tic[0])

                if (tic[2]-tic[0]) > 2:
                    prev_task_pos = indy_master.get_task_pos()
                    break
            
            indy_master.stop_jog()
            reset_cmd()


        if cmd == 2:
            prev_task_pos = indy_master.get_task_pos()
            reset_cmd()

        sleep(0.05)
    
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    main()
