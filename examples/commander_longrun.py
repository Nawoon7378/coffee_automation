from indy_utils.indy_shm import *

import json
from time import sleep
import threading
import numpy as np
import signal, sys

indy_master = IndyShmCommand()
COMMANDER_ADDR = 600

GFLAG = dict(run=True)

def reset_cmd():
    sleep(0.01)
    indy_master.write_direct_variable(0, COMMANDER_ADDR, 0)

def main():
    point = 0
    while GFLAG['run']:
        time.sleep(0.02)

        if point == 0:
            indy_master.write_direct_variable(4, 100, 0.350) # x
            indy_master.write_direct_variable(4, 101, -0.1865) # y
            indy_master.write_direct_variable(4, 102, 0.522) # z
            indy_master.write_direct_variable(4, 103, 0) # u
            indy_master.write_direct_variable(4, 104, 180) # v
            indy_master.write_direct_variable(4, 105, 0) # w
            indy_master.write_direct_variable(4, 106, 5) # vel
            indy_master.write_direct_variable(4, 107, 2) # acc

            point = 1

        elif point == 1:
            indy_master.write_direct_variable(4, 100, 0.200) # x
            indy_master.write_direct_variable(4, 101, -0.1065) # y
            indy_master.write_direct_variable(4, 102, 0.590) # z
            indy_master.write_direct_variable(4, 103, 0) # u
            indy_master.write_direct_variable(4, 104, 180) # v
            indy_master.write_direct_variable(4, 105, 0) # w
            indy_master.write_direct_variable(4, 106, 5) # vel
            indy_master.write_direct_variable(4, 107, 2) # acc
            point = 0

        indy_master.write_direct_variable(0, COMMANDER_ADDR, 1)

        while True:
            cmd = indy_master.read_direct_variable(0, COMMANDER_ADDR)
            if cmd == 0:
                break 
            else:
                sleep(0.01)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    GFLAG['run'] = False
    sys.exit(-1)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    main()
