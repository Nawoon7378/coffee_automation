
import json
from time import sleep
import time
import threading
import numpy as np
import signal, sys, os
import pickle

import logging


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

THREAD_LIST = []
GFLAG = dict(run=True)



def test_thr0():
    while GFLAG['run']:
        print("hello")
        sleep(1)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    print('hi')
    
    global THREAD_LIST

    GFLAG['run'] = False
    for th in THREAD_LIST:
        print("kill_thread")
        th.join()

    sys.exit(0)

if __name__ == "__main__":
    os.system("taskset -p -c 0,1 %d" % os.getpid())

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    # signal.signal(signal.SIGKILL, sig_handler)

    th0 = threading.Thread(target=test_thr0)
    th0.start()
    THREAD_LIST.append(th0)

