from indy_utils.indy_shm import *
import time

import json
from time import sleep
import signal, sys
import threading
import numpy as np

indy_master = IndyShmCommand()

COMMANDER_ADDR = 600
def conty_cmd(cmd):
    from time import sleep

    indy_master.write_direct_variable(0, COMMANDER_ADDR, cmd)
    while True:
        if indy_master.read_direct_variable(0, COMMANDER_ADDR) == 0:
            break
        else:
            sleep(0.05)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    indy_master.stop_jog()
    sys.exit(-1)

def watch():
    flag = False
    toc = 0
    while True:
        while indy_master.get_robot_status()['busy']:
            sleep(0.001)
        tic = time.time()
        print(tic-toc)

        while not indy_master.get_robot_status()['busy']:
            sleep(0.001)
        toc = time.time()
        print(toc-tic)


def main():
    while True:
        conty_cmd(1)
        conty_cmd(2)
    
if __name__ == "__main__":
    th0 = threading.Thread(target=watch)
    th0.start() 

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    main()