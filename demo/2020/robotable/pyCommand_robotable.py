#-*- coding: utf-8 -*-

from indy_utils.indy_shm import *
import threading
from time import sleep
import signal, sys

indy_master = IndyShmCommand()
GFLAG = dict(run=True)

def wait_for_motion_finish():
    # 로봇 모션이 종료될떄까지 대기
    while indy_master.get_robot_status()['busy']:
        pass

def reset_cmd():
    # 커맨드 종료 후 0으로 초기화
    sleep(0.01)
    indy_master.write_direct_variable(0, 200, 0)

def do_set(addr, val):
    do_set = indy_master.get_do()
    do_set[addr] = val
    indy_master.set_do(do_set)

def tray0():
    # 트레이0 상승 로직 
    while GFLAG['run']:
        # 현재 do list get
        # di[12] 와 di[13] 이 둘다 1이 아닐때
        if not indy_master.get_di()[12] and not indy_master.get_di()[13]:
            # do_set 에서 01 1로 set
            do_set(1, 1)
        # if 문에 해당하는 경우가 될때까지 대기
        while True:
            if indy_master.get_di()[0]:
                break
            if indy_master.get_di()[12]:
                break
            if indy_master.get_di()[13]:
                break
            if indy_master.get_di()[14]:
                break 
            sleep(0.05)
        # do_set 에서 01 0로 set
        do_set(1, 0)
        # loop문에 sleep 필요
        sleep(0.05)

def extra_dio():
    while GFLAG['run']:
        # extra di get
        di_el1008 = indy_master.get_el1008_di()
        # extra di 를 직접변수 B001 ~ B008 까지 할당
        for i in range(8):
            indy_master.write_direct_variable(0, i+1, di_el1008[i])

        # 직접변수 B101 ~ B108 get
        do_el2008 = indy_master.read_direct_variable(0, 101, 8)
        # 직접변수 B101 ~ B108 를 extra do 에 할당
        indy_master.set_el2008_do(do_el2008)
        sleep(0.05)

def main():
    while GFLAG['run']:
        time.sleep(0.02)
        cmd = indy_master.read_direct_variable(0, 200)
        
        if cmd == 1:
            reset_cmd()
        elif cmd ==2:
            pass
            reset_cmd()
        elif cmd == 3:
            pass
            reset_cmd()
        elif cmd == 3:
            pass
            reset_cmd()
        else:
            pass

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    GFLAG['run'] = False
    thr_io.join()
    thr0.join()    
    sys.exit(-1)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    thr_io = threading.Thread(target=extra_dio)
    thr0 = threading.Thread(target=tray0)

    thr_io.start()
    thr0.start()
    
    main()
