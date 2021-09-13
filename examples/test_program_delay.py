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
    while True:
        sleep(0.001)
####################################################################
# test 1
        if indy_master.read_direct_variable(0, 201) == 1:
            indy_master.write_direct_variable(0, 201, 0)
            tic = time.time()
            
            while True:
                sleep(0.001)
                if indy_master.read_direct_variable(0, 201) == 2:
                    break

            toc = time.time()
            indy_master.write_direct_variable(0, 201, 0)
            if toc - tic > 0.07:
                logger.info("test1, {}, without waitfor delay".format(round(toc - tic, 3)))


        if indy_master.read_direct_variable(0, 201) == 3:
            tic = time.time()
            indy_master.write_direct_variable(0, 201, 0)
            
            while True:
                sleep(0.001)
                if indy_master.read_direct_variable(0, 201) == 4:
                    break

            toc = time.time()
            indy_master.write_direct_variable(0, 201, 0)
            # logger.info("test1, {}, with waitfor delay".format(round(toc - tic, 3)))
####################################################################
# test 2

        
        if indy_master.read_direct_variable(0, 202) == 1:
            logger.info("test2 : ok")
            indy_master.write_direct_variable(0, 202, 0)
        
        if indy_master.read_direct_variable(0, 202) == 2:
            logger.info("test2 : modbus update error !!!")
            indy_master.write_direct_variable(0, 202, 0)

####################################################################
# test 3

        if indy_master.read_direct_variable(0, 203) == 1:
            indy_master.write_direct_variable(0, 203, 0)
            tic = time.time()

            while True:
                sleep(0.001)
                if indy_master.read_direct_variable(10, 103) == 1:
                    break
            
            indy_master.write_direct_variable(10, 103, 0)
            
            while True:
                sleep(0.001)
                if indy_master.read_direct_variable(0, 203) == 2:
                    break

            toc = time.time()
            indy_master.write_direct_variable(0, 203, 0)
            # if toc - tic > 0.15:
            # logger.info("test3, {}, communication delay".format(round(toc - tic, 3)))
####################################################################

if __name__ == "__main__":
    # th0 = threading.Thread(target=watch)
    # th0.start() 

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    os.system("taskset -p -c 0,1 %d" % os.getpid())

    main()

