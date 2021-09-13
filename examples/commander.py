from indy_utils.indy_shm import *

import json
from time import sleep
import threading
import numpy as np
import signal, sys

indy_master = IndyShmCommand()
COMMANDER_ADDR = 600

GFLAG = dict(run=True)

def wait_for_motion_finish():
    while indy_master.get_robot_status()['busy']:
        pass

def reset_cmd():
    sleep(0.01)
    indy_master.write_direct_variable(0, COMMANDER_ADDR, 0)

def main():
    while GFLAG['run']:
        time.sleep(0.02)
        cmd = indy_master.read_direct_variable(0, COMMANDER_ADDR)
        
        if cmd == 1:
            wait_for_motion_finish()
            indy_master.set_reference_frame([0,0,0.1,0,0,0])
            reset_cmd()
        elif cmd ==2:
            wait_for_motion_finish()
            indy_master.set_reference_frame([0,0,0.2,0,0,0])
            reset_cmd()
        elif cmd == 3:
            wait_for_motion_finish()
            indy_master.set_reference_frame([0,0,0,0,0,0])
            reset_cmd()
        elif cmd == 3:
            indy_master.ext_move_txt_file("/home/user/release/TasksDeployment/traj/210054_sstraj.txt")
            reset_cmd()
        else:
            pass

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    GFLAG['run'] = False
    sys.exit(-1)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    main()
