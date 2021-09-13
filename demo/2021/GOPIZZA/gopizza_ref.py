from indy_utils.indy_shm import *
from zmqsocket import *

import json
from time import sleep
import time
import threading
import numpy as np
import signal, sys, os
import pickle

import logging
import datetime

GFLAG = dict(
    run=True,
    pause=True,
)

########################################################
# vision
########################################################
class Receiver :
    def __init__(self,pub_adr,pub_port) :
        self.receiver = TcpSubscriber(pub_adr,pub_port,topic_name='pizza_info')
        self.receiver.connect('tcp://{}:{}'.format(pub_adr,pub_port))
        self._thread = threading.Thread(target=self._run,args=())
        self._thread.daemon = True
        self._thread.start()
        self._data = None

    def receive(self):
        return self._data

    def _run(self):
        while GFLAG['run']:
            self._data = self.receiver.receive()

vision_client = Receiver("192.168.1.6", "50009") #receiver 객체 생성 부탁드립니다. 
vision_pub = TcpPublisher(_HOST="192.168.1.23232", _PORT="50010") # step ip 입력

# vision_pub.send('1')

pizza_sauce_dict = dict(
    Nothing=0,
    Mayo=1,
    Teri=2,
    Renchi=3,
)

def cm_to_meter(pixel_int):
    return float(pixel_int)*0.01

def get_vision_data():
    cnt = 0
    while GFLAG['run']:
        cnt = cnt + 1
        if cnt > 10:
            return 250, [0,0,0,0,0,0] # disconnected

        socket_msg = vision_client.receive()
        if socket_msg is not None and not b'':
            _, jsonData = socket_msg
            pizza_dict = json.loads(jsonData)

            # 소스 뿌려야하는것
            # 뿌리지 말아야하는것
            # 그냥 통과시켜야하는것
            
            pizza_cutting = pizza_dict['cutting'] # true / false
            pizza_sauce = pizza_sauce_dict[pizza_dict['sauce']] 
            pizza_pos = [
                cm_to_meter(pizza_dict['center_point']['x']), 
                cm_to_meter(pizza_dict['center_point']['y']), 
                0, 
                0, 
                0, 
                pizza_dict['angle']
            ]
            
            return pizza_cutting, pizza_sauce, pizza_pos
########################################################



#########################################################
# 로거 설정
#########################################################
logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s, %(message)s')

# log 출력
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

now = datetime.datetime.now()

# # log 파일출력
# file_handler = logging.FileHandler('/home/user/release/TasksDeployment/PythonScript/{}.log'.format(now.strftime("%Y-%m-%d-%H-%M-%S")))
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)
#########################################################

CWD = os.getcwd()
DATA_DIR = os.path.join(CWD, 'saved_state.pickle')


THREAD_LIST = []
EL2008_DO_LIST = [0,0,0,0,0,0,0,0]

DIS = [0 for i in range(16)]

CUTTING_CMD_ADDR = 700
DESTACKER_CMD_ADDR = 701
PYTHON_READY_ADDR = 702
RECENT_TASK_ADDR = 703
RECENT_WARMER_ADDR = 704
RESERVE_PIZZA_ADDR = 705
CUTTING_MOTION_COLLISION_ADDR = 706
REFERENCE_UPDATE_CMD = 707
PIZZA_CATEGORY = 708
CUTTING_MOTION_ADDR = 709

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
    gate_0_time=-1,
    gate_1_time=-1,
    recent_pizza_sauce=0,
    recent_pizza_cut=0,
    recent_pizza_pos=[0,0,0,0,0,0],
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

    drizzle_power = 8,
    drizzle_0 = 9,
    drizzle_1 = 10,
    drizzle_2 = 11,
    drizzle_3 = 12,
    drizzle_4 = 13,
    drizzle_5 = 14,

    alarm = 15,
)

EL2008_DO_DICT = dict(
    stopper_0_power = 0,
    stopper_0_way = 1,

    stopper_1_power = 2,
    stopper_1_way = 3,

    lamp_green = 4,
    lamp_yellow = 5,
    lamp_red = 6,
)

DI_DICT = dict(
    gate_0_pizza = 0,
    gate_1_pizza = 1,

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

    botton_0_toggle = 12, # program_stop & direct_teaching on/off
    botton_1 = 13,        # program start & alarm reset
    botton_2_toggle = 14, # program pause/resume
    botton_3_toggle = 15, # warmer save on/off
)

EL1008_DI_DICT = dict()

indy_master = IndyShmCommand()
indy_master.set_sync_mode(True)

def init_DO():
  
    indy_master.set_do(DO_DICT['pusher_power'], 0)

    indy_master.set_do(DO_DICT['destacker_up'], 0)
    indy_master.set_do(DO_DICT['destacker_down'], 0)

    indy_master.set_do(DO_DICT['cutting_station_up'], 0)
    indy_master.set_do(DO_DICT['cutting_station_down'], 0)

    indy_master.set_do(DO_DICT['alarm'], 0)
    indy_master.set_do(DO_DICT['mini_conv'], 1)
    indy_master.set_do(DO_DICT['main_conv'], 1)

    indy_master.set_el2008_do([0,0,0,0,0,0,0,0])

def end_DO():
    indy_master.set_do(DO_DICT['pusher_power'], 0)

    indy_master.set_do(DO_DICT['destacker_up'], 0)
    indy_master.set_do(DO_DICT['destacker_down'], 0)

    indy_master.set_do(DO_DICT['cutting_station_up'], 0)
    indy_master.set_do(DO_DICT['cutting_station_down'], 0)

    indy_master.set_do(DO_DICT['alarm'], 0)
    indy_master.set_do(DO_DICT['mini_conv'], 0)
    indy_master.set_do(DO_DICT['main_conv'], 0)

    indy_master.set_el2008_do([0,0,0,0,0,0,0,0])

def motor_move(on_addr, limit_addr):
    indy_master.set_do(on_addr, 1)
    while GFLAG['run']:
        if DIS[limit_addr]:
            indy_master.set_do(on_addr, 0)
            break
        sleep(0.001)
    sleep(0.1)

def motor_move_gate(power_on_addr, way_addr, way, sleeptime):
    global EL2008_DO_LIST
    EL2008_DO_LIST[way_addr] = way
    EL2008_DO_LIST[power_on_addr] = 1

    indy_master.set_el2008_do(EL2008_DO_LIST)
    sleep(sleeptime)
    EL2008_DO_LIST[power_on_addr] = 0
    indy_master.set_el2008_do(EL2008_DO_LIST)


def commander():
    def get_new_pos(teaching_pos):
        return [teaching_pos[i] + STATE["recent_pizza_pos"][i] for i in range(6)]
    
    reference_pos = [0.41277365183882636, -0.5322269736781977, 0.00246840915363083, -1.6667774615421347, -178.8534617795961, 105.04854691702896]

    while GFLAG['run']:
        if indy_master.read_direct_variable(0, CUTTING_MOTION_ADDR) == 1:
            indy_master.set_collision_level(6)
            indy_master.set_reference_frame(reference_pos)
            sleep(0.1)
            indy_master.task_move_to(get_new_pos([0.0052, -0.0477, -0.0144, -19.8836, 1.0137, 0.2192])) # tilt 1
            indy_master.task_move_to(get_new_pos([0, 0, 0, 0, 0, 0])) # cut start
            indy_master.task_move_to(get_new_pos([0.0026, 0.0249, -0.0103, 24.9906, 0.6504, 0.3277])) # tilt 2
            indy_master.task_move_to(get_new_pos([0, 0, 0, 0, 0, 0])) # cut end

            while indy_master.get_robot_status()['busy']:
                sleep(0.01)

            sleep(0.1)
            indy_master.set_collision_level(5)
            sleep(0.1)
            indy_master.set_reference_frame([0,0,0,0,0,0])
            sleep(0.1)
            indy_master.write_direct_variable(0, CUTTING_MOTION_ADDR, 0)

def state_manager_thr():
    # 맨처음 한번 read, 실행되는 동안은 저장
    try:
        with open(DATA_DIR, 'rb') as f:
            SAVED_STATE.update(pickle.load(f))
    except:
        pass
    
    indy_master.write_direct_variable(0, RECENT_TASK_ADDR, SAVED_STATE['robot'])
    indy_master.write_direct_variable(0, RECENT_WARMER_ADDR, SAVED_STATE['recent_warmer'])
    
    GFLAG['pause'] = False
    indy_master.set_reference_frame([0,0,0,0,0,0])

    indy_master.write_direct_variable(0, PYTHON_READY_ADDR, 1)

    while GFLAG['run']:
        sleep(0.1)

        # switch 
        if DIS[DI_DICT['botton_1']] == 1:
            indy_master.set_do(DO_DICT['alarm'], 0)
            
        if DIS[DI_DICT['botton_2_toggle']] == 1:
            GFLAG['pause'] = True
            indy_master.set_do(DO_DICT['mini_conv'], 0)
            indy_master.set_do(DO_DICT['main_conv'], 0)

        if DIS[DI_DICT['botton_2_toggle']] == 0:
            indy_master.set_do(DO_DICT['main_conv'], 1)
            GFLAG['pause'] = False

        # save state 
        SAVED_STATE['robot'] = indy_master.read_direct_variable(0, RECENT_TASK_ADDR)
        SAVED_STATE['recent_warmer'] = indy_master.read_direct_variable(0, RECENT_WARMER_ADDR)

        with open(DATA_DIR, 'wb') as f:
            pickle.dump(SAVED_STATE, f, pickle.HIGHEST_PROTOCOL)
 
def di_update_thr():
    global DIS
    while GFLAG['run']:
        DIS = indy_master.get_di()
        sleep(0.01)


def gate_thr():
    # open ( 초기화 )
    motor_move_gate(EL2008_DO_DICT['stopper_0_power'], EL2008_DO_DICT['stopper_0_way'], 1, 0.7) #open
    motor_move_gate(EL2008_DO_DICT['stopper_1_power'], EL2008_DO_DICT['stopper_1_way'], 0, 0.7) #open

    while GFLAG['run']:
        sleep(0.01)
        while GFLAG['pause'] and GFLAG['run']:
            sleep(0.1)

        if STATE['gate_0_time'] > 0 and STATE['gate_1_time'] > 0:
            time_diff = abs(STATE['gate_0_time'] - STATE['gate_1_time'])
            if time_diff < 15:
                if STATE['gate_0_time'] < STATE['gate_1_time']:
                    motor_move_gate(EL2008_DO_DICT['stopper_0_power'], EL2008_DO_DICT['stopper_0_way'], 0, 0.5) #close
                    sleep(15-time_diff)
                    motor_move_gate(EL2008_DO_DICT['stopper_0_power'], EL2008_DO_DICT['stopper_0_way'], 1, 0.7) #open
                else:
                    motor_move_gate(EL2008_DO_DICT['stopper_1_power'], EL2008_DO_DICT['stopper_1_way'], 1, 0.5) #close
                    sleep(15-time_diff)
                    motor_move_gate(EL2008_DO_DICT['stopper_1_power'], EL2008_DO_DICT['stopper_1_way'], 0, 0.7) #open

def gate_sensor_thr():
    STATE['gate_0_time'] = -1
    STATE['gate_1_time'] = -1

    stopwatch_0 = False
    stopwatch_1 = False

    while GFLAG['run']:
        if DIS[DI_DICT['gate_0_pizza']] == 1 and stopwatch_0 == False:
            stopwatch_0 = True
            STATE['gate_0_time'] = time.time()
        elif DIS[DI_DICT['gate_0_pizza']] == 0:
            STATE['gate_0_time'] = -1
            stopwatch_0 = False

        if DIS[DI_DICT['gate_1_pizza']] == 1 and stopwatch_1 == False:
            stopwatch_1 = True
            STATE['gate_1_time'] = time.time()
        elif DIS[DI_DICT['gate_1_pizza']] == 0:
            STATE['gate_1_time'] = -1
            stopwatch_1 = False
            
        sleep(0.01)

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
            sleep(3)

            STATE['recent_pizza_cat'], STATE['recent_pizza_pos'] = get_vision_data()
            logging.info("cat : {}, pos : {}".format(STATE['recent_pizza_cat'], STATE['recent_pizza_pos']))

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
            indy_master.set_do(DO_DICT['cutting_station_down'], 1)
            sleep(3)
            indy_master.set_do(DO_DICT['cutting_station_down'], 0)
            sleep(0.5)
            motor_move(DO_DICT['cutting_station_up'], DI_DICT['cutting_station_middle'])
            indy_master.write_direct_variable(0, CUTTING_CMD_ADDR, 1)
            STATE['main_conv'] = 0
        
        elif cmd == 1:
            if STATE['main_conv'] == 1:
                sleep(4)
                if STATE['recent_pizza_cat'] > 99:
                    # 인식실패, disconneted 등
                    indy_master.write_direct_variable(0, CUTTING_CMD_ADDR, 0)
                else:
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

#     th4 = threading.Thread(target=gate_thr)
#     th4.start()
#     THREAD_LIST.append(th4)

#     th45 = threading.Thread(target=gate_sensor_thr)
#     th45.start()
#     THREAD_LIST.append(th45)

    th5 = threading.Thread(target=mini_conv_thr)
    th5.start()
    THREAD_LIST.append(th5)

    th = threading.Thread(target=state_manager_thr)
    th.start()
    THREAD_LIST.append(th)

    th18 = threading.Thread(target=commander)
    th18.start()
    THREAD_LIST.append(th18)
