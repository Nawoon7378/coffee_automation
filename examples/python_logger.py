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

# log 콘솔출력
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# log 파일출력
file_handler = logging.FileHandler('/home/user/release/TasksDeployment/PythonScript/robot_log.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info("'time', 'task_time', x, y, z, M057, M058")


def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    sys.exit(-1)

def main():
    while True:
        sleep(0.001)
        current_pos = indy_master.get_task_pos()
        rt_data = indy_master.get_rt_data()
        
        modbus57 = indy_master.read_direct_variable(10, 57)
        modbus58 = indy_master.read_direct_variable(10, 58)

        logger.info("{}, {}, {}, {}, {}, {}, {}".format(round(rt_data['time'], 2), rt_data['task_time'], current_pos[0], current_pos[1], current_pos[2], modbus57, modbus58))

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    os.system("taskset -p -c 0,1 %d" % os.getpid())

    main()

