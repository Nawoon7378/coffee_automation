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
    toc_ = time.time()
    while indy_master.get_robot_status()["busy"]:
        tic_ = time.time()
        if tic_ - toc_ > 0.05:
            print(tic_ - toc_)
        toc_ = tic_


def reset_cmd():
    sleep(0.05)
    indy_master.write_direct_variable(0, COMMANDER_ADDR, 0)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    indy_master.stop_motion()
    sys.exit(-1)

def main():
    indy_master.set_sync_mode(False)

    while True:
        tic[0] = time.time()
        indy_master.joint_move_to([0,0,0,0,0,0])
        
        while not indy_master.get_robot_status()["busy"]:
            sleep(0.001)
        tic[1] = time.time()
        
        wait_for_motion_finish()
        tic[2] = time.time()

        indy_master.joint_move_to([0,90,90,0,0,0])
        while not indy_master.get_robot_status()["busy"]:
            sleep(0.001)
        tic[3] = time.time()

        wait_for_motion_finish()
        tic[4] = time.time()
        
        indy_master.get_di()
        tic[5] = time.time()
        indy_master.set_reference_frame([0,0,0,0,0,0])
        tic[6] = time.time()
        indy_master.read_direct_variable(0, 1)
        tic[7] = time.time()


        for i in range(1, len(tic)):
            print("{} - {}".format(i, i-1), tic[i] - tic[i-1])

        print("entire", tic[7] - tic[0])
    
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    main()
