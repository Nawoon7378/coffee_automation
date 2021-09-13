from indy_utils.indy_shm import *
from zmqsocket import *
from dio_map_sangsu import *

import json
from time import sleep
import time
import threading
import numpy as np
import signal, sys, os
import pickle

import logging
import datetime

# DIO Config 
# 버튼 0 : program stop, error reset, direct teaching
# 버튼 1 : 프로그램 시작, 알람 리셋
# 버튼 2 : 프로그램 pasue
# 버튼 3 : 가져다 둘지 안할지 

CWD = os.getcwd()
DATA_DIR = os.path.join(CWD, 'saved_state.pickle')

indy_master = IndyShmCommand()
indy_master.set_sync_mode(False)

########################################################
# global variable
########################################################
GFLAG = dict(
    run=True,
    pause=True,
)

THREAD_LIST = []
EL2008_DO_LIST = [0,0,0,0,0,0,0,0]

DIS = [0 for i in range(16)]

CUTTING_CMD_ADDR = 700
PYTHON_READY_ADDR = 702
RECENT_TASK_ADDR = 703
RECENT_WARMER_ADDR = 704
MOTION_ADDR = 709

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
vision_pub = TcpPublisher(_HOST="192.168.1.7", _PORT="50010") # step ip 입력

pizza_sauce_dict = dict(
    Nothing=0,
    Mayo=1,
    Teri=5,
    Renchi=10,
)

def cm_to_meter(pixel_int):
    return float(pixel_int)*0.01

def get_vision_data():
    cnt = 0
    pizza_cutting = 0
    pizza_sauce = 0
    pizza_pos = [0,0,0,0,0,0]
    pizza_drizzle_pos = []

    while GFLAG['run']:
        cnt = cnt + 1
        if cnt > 10:
            break

        socket_msg = vision_client.receive()
        if socket_msg is not None and not b'':
            _, jsonData = socket_msg
            pizza_dict = json.loads(jsonData)

            try:
                pizza_cutting = pizza_dict['cutting'] # true / false
                sauce_list = pizza_dict['sauce']

                pizza_sauce = 0

                for s in sauce_list:
                    pizza_sauce = pizza_sauce + pizza_sauce_dict[s]

                pizza_pos = [
                    cm_to_meter(pizza_dict['center_point']['x']), 
                    cm_to_meter(pizza_dict['center_point']['y']), 
                    0, 
                    0, 
                    0, 
                    pizza_dict['angle']
                ]
                
                pizza_drizzle_pos = [(cm_to_meter(item[0]), cm_to_meter(item[1])) for item in pizza_dict['drizzle']]
                print(pizza_drizzle_pos)
                break
            except:
                pizza_cutting = 0
                pizza_sauce = 0
                pizza_pos = [0,0,0,0,0,0]
                pizza_drizzle_pos = []
                break

    STATE['recent_pizza_cutting'] = pizza_cutting
    STATE['recent_pizza_sauce'] = pizza_sauce
    STATE['recent_pizza_pos'] = pizza_pos
    STATE['recent_pizza_drizzle_pos'] = pizza_drizzle_pos
    vision_pub.send('1')

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
    # recent_pizza_cat=250,
    recent_pizza_cutting=0,
    recent_pizza_sauce=0,
    recent_pizza_pos=[0,0,0,0,0,0],
    recent_pizza_drizzle_pos = [],
)

SAVED_STATE=dict(
    # 파일저장/불러오기 하려고 따로 지정
    # 로봇 - 0: 커팅 레디, 1: 커팅, 2: 드리즐, 3: 픽, 4: 플레이스
    robot=0,
    # 최근에 로봇이 작업한 온장고 - 0: 0번위치 저장 됨, 1: 1번위치 저장 됨 2, 3 동일
    recent_warmer=0
)

def commander():
    def get_new_pos(teaching_pos):
        return [teaching_pos[i] + STATE["recent_pizza_pos"][i] for i in range(6)]

    def custom_task_move(pos):
        if GFLAG['run'] == False:
            sleep(1)
            end_do(indy_master)
            os.kill(os.getpid(), 9)

        indy_master.task_move_to(pos) 

        while GFLAG['run']: 
            status = indy_master.get_robot_status()
            if not status['busy'] and status['movedone']:
                break
            sleep(0.01)

    reference_pos = [0.4131141403902718, -0.5325020788499358, 0.0032157837802533297, -1.6274975580173918, -178.79480734324068, 105.05736955396992]
    
    while GFLAG['run']:
        if indy_master.read_direct_variable(0, MOTION_ADDR) == 1:
            indy_master.set_collision_level(6)
            sleep(0.1)
            indy_master.set_reference_frame(reference_pos)
            sleep(0.1)

            custom_task_move(get_new_pos([0.00679, 0.04349, -0.0056, -157.65912, -179.68399, 179.0201])) #tilt1
            custom_task_move(get_new_pos([0, 0, 0, 0, 0, 0]))
            custom_task_move(get_new_pos([0.00124, -0.03714, -0.01298, 160.110, 179.674, 179.336]))   #tilt2
            custom_task_move(get_new_pos([0, 0, 0, 0, 0, 0]))

            sleep(0.1)
            indy_master.set_collision_level(5)
            sleep(0.1)
            indy_master.set_reference_frame([0,0,0,0,0,0])
            sleep(0.1)
            indy_master.write_direct_variable(0, MOTION_ADDR, 0)

        elif indy_master.read_direct_variable(0, MOTION_ADDR) == 2:
            if STATE['recent_pizza_sauce']:
                sleep(0.1)
                indy_master.set_reference_frame([0,0,0,0,0,0])
                sleep(0.1)
                origin_pos = indy_master.get_task_pos()
                sleep(0.1)
                indy_master.set_reference_frame(origin_pos)


                for drizzle_pos in STATE['recent_pizza_drizzle_pos']:
                    # new_pos = [p for p in origin_pos]
                    new_pos = [0,0,0,0,0,0]
                    new_pos[0] = new_pos[0] + drizzle_pos[0]
                    new_pos[1] = new_pos[1] + drizzle_pos[1]
                    custom_task_move(new_pos)
                    # drizzle on 소스 종류에 맞게

                # drizzle off 소스 종류에 맞게    

            indy_master.write_direct_variable(0, MOTION_ADDR, 0)



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
        if is_botton_1(DIS):
            alarm_off(indy_master)
            
        if is_botton_2_toggle(DIS):
            GFLAG['pause'] = True
            mini_conv_stop(indy_master)
            main_conv_stop(indy_master)

        if not is_botton_2_toggle(DIS):
            GFLAG['pause'] = False
            main_conv_move(indy_master)

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
    global EL2008_DO_LIST

    def gate_0_open_auto():
        gate_0_open(indy_master, EL2008_DO_LIST)
        sleep(0.7)
        gate_0_stop(indy_master, EL2008_DO_LIST)

    def gate_0_close_auto():
        gate_0_close(indy_master, EL2008_DO_LIST)
        sleep(0.7)
        gate_0_stop(indy_master, EL2008_DO_LIST)

    def gate_1_open_auto():
        gate_1_open(indy_master, EL2008_DO_LIST)
        sleep(0.7)
        gate_1_stop(indy_master, EL2008_DO_LIST)

    def gate_1_close_auto():
        gate_1_close(indy_master, EL2008_DO_LIST)
        sleep(0.7)
        gate_1_stop(indy_master, EL2008_DO_LIST)

    gate_0_open_auto()
    gate_1_open_auto()

    while GFLAG['run']:
        sleep(0.01)
        while GFLAG['pause'] and GFLAG['run']:
            sleep(0.1)

        if STATE['gate_0_time'] > 0 and STATE['gate_1_time'] > 0:
            time_diff = abs(STATE['gate_0_time'] - STATE['gate_1_time'])
            if time_diff < 15:
                if STATE['gate_0_time'] < STATE['gate_1_time']:
                    gate_0_close_auto()
                    sleep(15-time_diff)
                    gate_0_open_auto()
                else:
                    gate_1_close_auto()
                    sleep(15-time_diff)
                    gate_1_open_auto()

def gate_sensor_thr():
    STATE['gate_0_time'] = -1
    STATE['gate_1_time'] = -1

    stopwatch_0 = False
    stopwatch_1 = False

    while GFLAG['run']:
        if is_gate_0_pizza_ready(DIS) and stopwatch_0 == False:
            stopwatch_0 = True
            STATE['gate_0_time'] = time.time()
        elif not is_gate_0_pizza_ready(DIS):
            STATE['gate_0_time'] = -1
            stopwatch_0 = False

        if is_gate_1_pizza_ready(DIS) and stopwatch_1 == False:
            stopwatch_1 = True
            STATE['gate_1_time'] = time.time()
        elif not is_gate_1_pizza_ready(DIS):
            STATE['gate_1_time'] = -1
            stopwatch_1 = False
            
        sleep(0.01)

def mini_conv_thr():
    while GFLAG['run']:
        while GFLAG['pause'] and GFLAG['run']:
            sleep(0.1)

        #destacker 에 피자 있을때는 멈춤
        if is_destacker_pizza_ready(DIS):
            mini_conv_stop(indy_master)
        else:
            mini_conv_move(indy_master)
            STATE['mini_conv'] = 0

        sleep(0.01)

def pusher_thr():
    while GFLAG['run']:
        while GFLAG['pause'] and GFLAG['run']:
            sleep(0.1)
        
        if (
                is_destacker_pizza_ready(DIS) and # destacker 에 피자 충전 됨,
                STATE['main_conv'] == 0 and # 커팅 스테이션 과 pusher 사이에 피자가 없는 상태
                STATE['destacker'] == 1 # destacker가 다 올라왔을때
        ):
            sleep(3)

            get_vision_data() 
            logging.info("cut : {}, sauce : {}, pos : {}".format(STATE['recent_pizza_cutting'], STATE['recent_pizza_sauce'], STATE['recent_pizza_pos']))

            pusher_push(indy_master)
            while GFLAG['run'] and not is_pusher_end(DIS):
                sleep(0.001)
            pusher_stop(indy_master)

            STATE['destacker'] = 0
            STATE['main_conv'] = 1

            pusher_back(indy_master)
            while GFLAG['run'] and not is_pusher_start(DIS):
                sleep(0.001)
            pusher_stop(indy_master)

        sleep(0.01)

def destacker_thr():
    while GFLAG['run']:
        if GFLAG['pause'] and STATE['destacker'] != 3: # down (사용자 입력)
            # 전체 일시정지상태가 되면 destacker는 내려감

            STATE['destacker'] = 3
            destacker_down(indy_master)
            while GFLAG['run'] and not is_destacker_bottom(DIS):
                sleep(0.001)
            destacker_stop(indy_master)

        if GFLAG['pause'] == False and STATE['destacker'] == 3:
            # 사용자가 디스태커 보충을 끝내고 resume 하면 디스태커 up
            STATE['destacker'] = 0

        if STATE['destacker'] == 0:
            if is_destacker_top(DIS):
                alarm_on(indy_master)
                STATE['destacker'] = 2
                continue

            elif is_destacker_plate_ready(DIS):
                STATE['destacker'] = 1
                continue

            else:
                sleep(0.7) # 접시가 얇아서 기다려야함
                destacker_up(indy_master)

                while GFLAG['run']:
                    if is_destacker_plate_ready(DIS):
                        destacker_stop(indy_master)
                        STATE['destacker'] = 1
                        break

                    if is_destacker_top(DIS):
                        # 디스태커 보충이 필요한 상황 -> pusher 일시정지
                        destacker_stop(indy_master)
                        alarm_on(indy_master)
                        STATE['destacker'] = 2
                        break

                    sleep(0.001)

        sleep(0.01)
        
def cutting_station_thr():
    while GFLAG['run']:
        while GFLAG['pause'] and GFLAG['run']:
            sleep(0.1)
        
        cmd = indy_master.read_direct_variable(0, CUTTING_CMD_ADDR)
        
        if cmd == 0 and not is_pick_ready(DIS): # pickup 위치가 비어있고, 명령이 들어왔을때만 다운
            cutting_station_down(indy_master)
            sleep(3)
            cutting_station_stop(indy_master)
            sleep(0.5)

            cutting_station_up(indy_master)
            while GFLAG['run'] and not is_cutting_station_middle(DIS):
                sleep(0.001)
            cutting_station_stop(indy_master)
            
            indy_master.write_direct_variable(0, CUTTING_CMD_ADDR, 1)
            STATE['main_conv'] = 0
        
        elif cmd == 1:
            if STATE['main_conv'] == 1:
                sleep(4)
                if not STATE['recent_pizza_cutting']:
                    # 인식실패, disconneted , cutting을 안하는경우
                    indy_master.write_direct_variable(0, CUTTING_CMD_ADDR, 0)
                else:
                    cutting_station_up(indy_master)
                    while GFLAG['run'] and not is_cutting_station_top(DIS):
                        sleep(0.001)
                    cutting_station_stop(indy_master)

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

    end_do(indy_master)

if __name__ == "__main__":
    
    os.system("taskset -p -c 0,1 %d" % os.getpid())

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    init_do(indy_master)

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

    th131 = threading.Thread(target=state_manager_thr)
    th131.start()
    THREAD_LIST.append(th131)

    th18 = threading.Thread(target=commander)
    th18.start()
    THREAD_LIST.append(th18)
