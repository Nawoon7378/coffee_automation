from indy_utils.indy_shm import *
import time

import json
from time import sleep
import signal, sys
import threading
import numpy as np

indy_master = IndyShmCommand()


def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    sys.exit(-1)


def main():
    while True:
        indy_master.set_do(15, 0) # DO 15 번 off
        sleep(0.5) # 0.5 sec wait

        indy_master.set_do(15, 1) # DO 15 번 on
        tic = time.time() # 시간 측정

        while not indy_master.get_di()[0] == 1: # DI 0 번이 1 이 될때까지 대기
            sleep(0.001)

        toc = time.time()  # 시간 측정
        print(toc-tic) # 측정된 시간 차 계산 및 출력
        sleep(0.5)

        
    
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    main()