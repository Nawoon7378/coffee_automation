from indy_utils.indy_shm import *

import json
import time
from time import sleep
import signal, sys, os
import threading
import numpy as np

import logging

indy_master = IndyShmCommand()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s, %(message)s')

# log 출력
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# log 파일출력
file_handler = logging.FileHandler('/home/user/release/TasksDeployment/PythonScript/modbus_delay.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    sys.exit(-1)

def main():
    time_0 = 0
    time_1 = 0
    while True:
        sleep(0.001)
        
        if indy_master.read_direct_variable(0, 600) == 1:
            indy_master.write_direct_variable(0, 600, 0)
            tic = time.time()
            
            while True:
                sleep(0.001)
                if indy_master.read_direct_variable(0, 600) == 2:
                    break

            toc = time.time()
            indy_master.write_direct_variable(0, 600, 0)
            time_0 = toc-tic

        if indy_master.read_direct_variable(0, 600) == 11:
            indy_master.write_direct_variable(0, 600, 0)
            tic = time.time()
            
            while True:
                sleep(0.001)
                if indy_master.read_direct_variable(0, 600) == 12:
                    break

            toc = time.time()
            indy_master.write_direct_variable(0, 600, 0)
            time_1 = toc-tic

            logger.info("{} delay".format(round(time_0 - time_1, 4)))
        

if __name__ == "__main__":
    # th0 = threading.Thread(target=watch)
    # th0.start() 

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    os.system("taskset -p -c 0,1 %d" % os.getpid())

    main()

