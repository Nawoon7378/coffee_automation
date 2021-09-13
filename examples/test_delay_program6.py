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
file_handler = logging.FileHandler('/home/user/release/TasksDeployment/PythonScript/modbus_delay_2.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    sys.exit(-1)

def main():

    while True:
        sleep(0.001)
        if indy_master.read_direct_variable(10, 54) == 1:
            indy_master.write_direct_variable(10, 54, 2)

        if indy_master.read_direct_variable(0, 600) == 1:
            indy_master.write_direct_variable(0, 600, 0)
            tic = time.time()
            
            while True:
                sleep(0.001)
                # if indy_master.read_direct_variable(10, 54) == 1:
                #     indy_master.write_direct_variable(10, 54, 2)

                # if indy_master.read_direct_variable(10, 57) == 1:
                indy_master.write_direct_variable(10, 57, 2)
                indy_master.write_direct_variable(10, 58, 2)

                if indy_master.read_direct_variable(0, 600) == 2:
                    break

            toc = time.time()
            indy_master.write_direct_variable(0, 600, 0)
            logger.info("{}".format(round(toc - tic, 3)))

if __name__ == "__main__":
    # th0 = threading.Thread(target=watch)
    # th0.start() 

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    os.system("taskset -p -c 0,1 %d" % os.getpid())

    main()

