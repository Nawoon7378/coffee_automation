from indy_utils.indy_shm import *

import json
from time import sleep
import time
import threading
import numpy as np
import signal, sys, os
import pickle

GFLAG = dict(
    run=True,
    pause=True,
)

THREAD_LIST = []
DIS = [0 for i in range(16)]

CUTTING_CMD_ADDR = 700
DESTACKER_CMD_ADDR = 701
PYTHON_READY_ADDR = 702

RECENT_TASK_ADDR = 703

RECENT_WARMER_ADDR = 704
RESERVE_PIZZA_ADDR = 705

CUTTING_MOTION_COLLISION_ADDR = 706
PIZZA_TYPE = 707

# TODO 
# 작업단계에 따른 초기화 전략 변경 필요 ( 사용자가 정지 -> 시작 버튼 클릭시 )

# 피자 종류에따른 드리즐 구분
# 비전 -> 파이썬 프로그램 -> 직접변수 -> 콘티 프로그램
# 피자 위치 
# x, y, theta -> 비전좌표계 기준 (비전은 고정)
# 해앙 위치로 참조좌표계 설정 및 티칭 

STATE = dict(
    # 고븐 - 0: 현재 인식중인 피자 없음, 1 : 1 개 인식, 2: 2개인식 (가장 최근)
    # 미니컨베이어 ( 고븐에서 피자 떨어진 후 디스태커에 투입되기 전 ) 
    # 메인컨베이어 ( pusher 와 cutting station 사이 ) - 0 피자 없음, 1 - 피자 있음
    # 디스태커 - 0: 디스태커 up 하는 중, 1: 플레이트 레디, 2: 디스태커 보충 필요 (끝까지 올라감), 3: 사용자가 디스태커 보충 중
    # 피자 저장여부 - 0: 저장안하고 cutting & drizzle 만 반복, 1: 만들어진 피자 온장고에 저장
    goven=0,
    mini_conv=0,
    main_conv=0,
    destacker=0,
    reserve_pizza=1, 
)

SAVED_STATE=dict(
    # 파일저장/불러오기 하려고 따로 지정
    # 로봇 - 0: 커팅 레디, 1: 커팅, 2: 드리즐, 3: 픽, 4: 플레이스
    robot=0,
    # 최근에 로봇이 작업한 온장고 - 0: 0번위치 저장 됨, 1: 1번위치 저장 됨 2, 3 동일
    recent_warmer=0
) 

DO_DICT = dict(
    mini_conv = 0,
    main_conv = 1,

    pusher_power=2,
    pusher_way=3,
    
    destacker_up=4,
    destacker_down=5,
    
    cutting_station_up=6,
    cutting_station_down=7,
    alarm = 15,

)

DI_DICT = dict(
    goven_0 = 0,
    goven_1 = 1,

    destacker_plate=2,
    destacker_pizza=3,

    pusher_start=4,
    pusher_end=5,
    
    destacker_bottom=6,
    destacker_top=7,

    cutting_station_bottom=8,
    cutting_station_middle=9,
    cutting_station_top=10,

    pickup_plate=11,
    program_run_toggle = 12,
    alarm_reset_button = 13,
    program_pause_toggle = 14,

    # button_2 = 16,
)

indy_master = IndyShmCommand()

def init_DO():
    indy_master.set_do(DO_DICT['pusher_power'], 0)

    indy_master.set_do(DO_DICT['destacker_up'], 0)
    indy_master.set_do(DO_DICT['destacker_down'], 0)

    indy_master.set_do(DO_DICT['cutting_station_up'], 0)
    indy_master.set_do(DO_DICT['cutting_station_down'], 0)

    indy_master.set_do(DO_DICT['alarm'], 0)
    indy_master.set_do(DO_DICT['mini_conv'], 1)
    indy_master.set_do(DO_DICT['main_conv'], 1)

def end_DO():
    indy_master.set_do(DO_DICT['pusher_power'], 0)

    indy_master.set_do(DO_DICT['destacker_up'], 0)
    indy_master.set_do(DO_DICT['destacker_down'], 0)

    indy_master.set_do(DO_DICT['cutting_station_up'], 0)
    indy_master.set_do(DO_DICT['cutting_station_down'], 0)

    indy_master.set_do(DO_DICT['alarm'], 0)
    indy_master.set_do(DO_DICT['mini_conv'], 0)
    indy_master.set_do(DO_DICT['main_conv'], 0)


def motor_move(on_addr, limit_addr):
    indy_master.set_do(on_addr, 1)
    while GFLAG['run']:
        if DIS[limit_addr]:
            indy_master.set_do(on_addr, 0)
            break
        sleep(0.001)
    sleep(0.1)

def state_manager_thr():
    # 맨처음 한번 read, 실행되는 동안은 저장
    try:
        with open('/home/user/release/TasksDeployment/PythonScript/data.pickle', 'rb') as f:
            SAVED_STATE.update(pickle.load(f))
    except:
        pass
    
    indy_master.write_direct_variable(0, RECENT_TASK_ADDR, SAVED_STATE['robot'])
    indy_master.write_direct_variable(0, RECENT_WARMER_ADDR, SAVED_STATE['recent_warmer'])
    
    GFLAG['pause'] = False
    indy_master.write_direct_variable(0, PYTHON_READY_ADDR, 1)

    pickup_alarm_flag = False

    while GFLAG['run']:
        sleep(0.5)

        indy_master.write_direct_variable(0, RESERVE_PIZZA_ADDR, STATE['reserve_pizza'])

        SAVED_STATE['robot'] = indy_master.read_direct_variable(0, RECENT_TASK_ADDR)
        SAVED_STATE['recent_warmer'] = indy_master.read_direct_variable(0, RECENT_WARMER_ADDR)

        # if (
        #     DIS[DI_DICT['pickup_plate']] == 1 and
        #     STATE['main_conv'] == 1 and
        #     DIS[DI_DICT['destacker_pizza']] == 1
        # ): # 꽉 차면 알람하고 사람부르기
        #     if DIS[DI_DICT['goven_0']] or DIS[DI_DICT['goven_1']]:
        #         # indy_master.set_do(DO_DICT['alarm'], 1)
        #         # STATE['reserve_pizza'] = 0
        #         pickup_alarm_flag = True

        # if pickup_alarm_flag and DIS[DI_DICT['pickup_plate']] == 0:
        #     # 꽉 차서 발생한 알람은 가져가면 끄기
        #     indy_master.set_do(DO_DICT['alarm'], 0)
        #     pickup_alarm_flag = False

        if DIS[DI_DICT['alarm_reset_button']] == 1:
            indy_master.set_do(DO_DICT['alarm'], 0)
            
        if DIS[DI_DICT['program_pause_toggle']] == 1:
            GFLAG['pause'] = True
            indy_master.set_do(DO_DICT['mini_conv'], 0)
            indy_master.set_do(DO_DICT['main_conv'], 0)

        if DIS[DI_DICT['program_pause_toggle']] == 0:
            indy_master.set_do(DO_DICT['main_conv'], 1)
            GFLAG['pause'] = False

        if indy_master.read_direct_variable(0, CUTTING_MOTION_COLLISION_ADDR) == 1:
            indy_master.set_collision_level(6)
            indy_master.write_direct_variable(0, CUTTING_MOTION_COLLISION_ADDR, 0)

        elif indy_master.read_direct_variable(0, CUTTING_MOTION_COLLISION_ADDR) == 2:
            indy_master.set_collision_level(5)
            indy_master.write_direct_variable(0, CUTTING_MOTION_COLLISION_ADDR, 0)
        else:
            pass

        with open('/home/user/release/TasksDeployment/PythonScript/data.pickle', 'wb') as f:
            pickle.dump(SAVED_STATE, f, pickle.HIGHEST_PROTOCOL)
 
def di_update_thr():
    global DIS
    while GFLAG['run']:
        DIS = indy_master.get_di()
        sleep(0.01)

def goven_thr():
    # stopper 없을때
    # 디스태커에 피자가 있고, cutting station 에도 피자가 있는데 피자가 더 들어오는 상황 -> 알람
    # while GFLAG['run']:
    #     if DIS[DI_DICT['destacker_pizza']] == 1 and STATE['main_conv'] == 1:
    #         if DIS[DI_DICT['goven_0']] == 1 or DIS[DI_DICT['goven_1']] == 1:
    #             indy_master.set_do(DO_DICT['alarm'], 1)
    #             pass
    #             # STATE['reserve_pizza'] = 0
    #         else:
    #             STATE['reserve_pizza'] = 1
    #     else:
    #         pass

        sleep(0.01)

    # stopper 있을때
    # while GFLAG['run']:
    #     first_in = ''
    #     # 먼저 들어온 stopper 확인
    #     while GFLAG['run']:
    #         if DIS[DI_DICT['stopper_0']] == 1:
    #             first_in = 'stopper_0'
    #             last_in = 'stopper_1'
    #             break
    #         if DIS[DI_DICT['stopper_1']] == 1:
    #             first_in = 'stopper_1'
    #             last_in = 'stopper_0'
    #             break
    #         sleep(0.01)

    #     indy_master.set_do[DO_DICT[last_in], 0]

    #     # 처음 들어온 것부터 open
    #     while GFLAG['run']:
    #         if STATE['mini_conv'] == 0:
    #             indy_master.set_do[DO_DICT[first_in], 1]
    #             STATE['mini_conv'] = 1
    #             sleep(5)
    #             break
    #         else:
    #             indy_master.set_do[DO_DICT[first_in], 0]
    #         sleep(0.01)
            
    #     while GFLAG['run']:
    #         if STATE['mini_conv'] == 0:
    #             indy_master.set_do[DO_DICT[last_in], 1]
    #             STATE['mini_conv'] = 1
    #             sleep(5)
    #             break
    #         else:
    #             indy_master.set_do[DO_DICT[last_in], 0]
    #         sleep(0.01)

    #     while GFLAG['run']:
    #         if DIS[DI_DICT['stopper_0']] == 0 and DIS[DI_DICT['stopper_1']] == 0:
    #             break
    #         sleep(0.01)
        
    #     sleep(0.01)

def mini_conv_thr():
    while GFLAG['run']:
        while GFLAG['pause'] and GFLAG['run']:
            sleep(0.1)

        #destacker 에 피자 있을때는 멈춤
        if DIS[DI_DICT['destacker_pizza']] == 1:
            indy_master.set_do(DO_DICT['mini_conv'], 0)
        else:
            indy_master.set_do(DO_DICT['mini_conv'], 1)
            STATE['mini_conv'] = 0

        sleep(0.01)

def pusher_thr():
    while GFLAG['run']:
        while GFLAG['pause'] and GFLAG['run']:
            sleep(0.1)
        
        if (
                DIS[DI_DICT['destacker_pizza']] == 1 and # destacker 에 피자 충전 됨,
                STATE['main_conv'] == 0 and # 커팅 스테이션 과 pusher 사이에 피자가 없는 상태
                STATE['destacker'] == 1 # destacker가 다 올라왔을때
        ):
            sleep(1)

            indy_master.set_do(DO_DICT['pusher_way'], 1)
            motor_move(DO_DICT['pusher_power'], DI_DICT['pusher_end'])
            STATE['destacker'] = 0
            STATE['main_conv'] = 1
            indy_master.set_do(DO_DICT['pusher_way'], 0)
            motor_move(DO_DICT['pusher_power'], DI_DICT['pusher_start'])

        sleep(0.01)



def destacker_thr():
    while GFLAG['run']:

        if GFLAG['pause'] and STATE['destacker'] != 3: # down (사용자 입력)
            # 전체 일시정지상태가 되면 destacker는 내려감

            STATE['destacker'] = 3
            motor_move(DO_DICT['destacker_down'], DI_DICT['destacker_bottom'])

        if GFLAG['pause'] == False and STATE['destacker'] == 3:
            # 사용자가 디스태커 보충을 끝내고 resume 하면 디스태커 up
            STATE['destacker'] = 0

        if STATE['destacker'] == 0:
            if DIS[DI_DICT['destacker_top']]:
                indy_master.set_do(DO_DICT['alarm'], 1)
                STATE['destacker'] = 2
                continue

            elif DIS[DI_DICT['destacker_plate']]:
                STATE['destacker'] = 1
                continue

            else:
                sleep(0.7) # 접시가 얇아서 기다려야함
                indy_master.set_do(DO_DICT['destacker_up'], 1)

                while True:
                    if DIS[DI_DICT['destacker_plate']]:
                        indy_master.set_do(DO_DICT['destacker_up'], 0)
                        STATE['destacker'] = 1
                        break

                    if DIS[DI_DICT['destacker_top']]:
                        # 디스태커 보충이 필요한 상황 -> pusher 일시정지
                        indy_master.set_do(DO_DICT['destacker_up'], 0)
                        indy_master.set_do(DO_DICT['alarm'], 1)
                        STATE['destacker'] = 2
                        break

                    sleep(0.001)

        sleep(0.01)
        
def cutting_station_thr():
    while GFLAG['run']:
        while GFLAG['pause'] and GFLAG['run']:
            sleep(0.1)
        
        cmd = indy_master.read_direct_variable(0, CUTTING_CMD_ADDR)
        if cmd == 0 and DIS[DI_DICT['pickup_plate']] == 0: # pickup 위치가 비어있고, 명령이 들어왔을때만 다운
            motor_move(DO_DICT['cutting_station_down'], DI_DICT['cutting_station_bottom'])
            sleep(0.75)
            motor_move(DO_DICT['cutting_station_up'], DI_DICT['cutting_station_middle'])
            indy_master.write_direct_variable(0, CUTTING_CMD_ADDR, 1)
            STATE['main_conv'] = 0
        
        elif cmd == 1:
            if STATE['main_conv'] == 1:
                # 당장은 push 되고 -> 3초 후 up
                sleep(3)
                motor_move(DO_DICT['cutting_station_up'], DI_DICT['cutting_station_top'])
                # 여기는 한번만 들어와야지
                indy_master.write_direct_variable(0, CUTTING_CMD_ADDR, 2)
        
        sleep(0.01)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    
    global THREAD_LIST

    GFLAG['run'] = False

    for th in THREAD_LIST:
        print("kill_thread")
        th.join()

    end_DO()
    sys.exit(-1)

if __name__ == "__main__":
    
    os.system("taskset -p -c 0,1 %d" % os.getpid())

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    init_DO()

    th0 = threading.Thread(target=pusher_thr)
    th0.start()
    THREAD_LIST.append(th0)

    th1 = threading.Thread(target=destacker_thr)
    th1.start()
    THREAD_LIST.append(th1)

    th2 = threading.Thread(target=cutting_station_thr)
    th2.start()
    THREAD_LIST.append(th2)

    th3 = threading.Thread(target=di_update_thr)
    th3.start()
    THREAD_LIST.append(th3)

    # th4 = threading.Thread(target=goven_thr)
    # th4.start()
    # THREAD_LIST.append(th4)

    th5 = threading.Thread(target=mini_conv_thr)
    th5.start()
    THREAD_LIST.append(th5)

    th = threading.Thread(target=state_manager_thr)
    th.start()
    THREAD_LIST.append(th)

