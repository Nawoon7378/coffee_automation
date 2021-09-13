from multiprocessing import Process, Queue
import os, glob, json, time, signal, threading, sys
import configparser
from indy_utils.indy_shm import *

print("Python start")

# Master robot
indy_master = IndyShmCommand()
indy_master.set_sync_mode(True)

# buffer_idx를 ini파일에 기록
config = configparser.ConfigParser()
inipath = '/home/user/dev/runtest/Release/TasksDeployment/PythonScript/Environment_.ini'

# DI Sensor on/off
sensor_on = 1
sensor_off = 0

# robot speed
joint_vel = 9
task_vel = 9


# 이전 Pick Up 위치
g_flst_pick_up_before = []

# Retry 하기위한 pickUp 위치
g_flst_pick_up_Retry = []

# Threshold
buffer_z_threshold = [-0.21, -0.21, -0.21]

# DO
endtool_cylinder_idx = 0
Press_on_idx = 1
buffer_exist = [2, 3, 4]
endtool_suction_idx = 5
endtool_blow_idx = 6
buffer_blow_idx = [7, 14, 15]
cylinder_up_idx = [8, 10, 12]
cylinder_down_idx = [9, 11, 13]

# DI
endtool_sensor_idx = 2
cylinder_fwd_sensor_idx = [4, 7, 10]
cylinder_up_sensor = [3, 6, 9]
buffer_object_sensor = [5, 8, 11]

# AI
load_cell_idx = 0

# Indy Move Type
MOVE_TYPE_JOINT = 0
MOVE_TYPE_TASK = 1

g_nPickRetryCnt = 0

g_Press_done = False

COMMANDER_ADDR = 600
def conty_cmd(cmd):
    from time import sleep

    indy_master.write_direct_variable(0, COMMANDER_ADDR, cmd)
    while True:
        if indy_master.read_direct_variable(0, COMMANDER_ADDR) == 0:
            break
        else:
            sleep(0.05)

def main():
    global g_flst_pick_up_before
    global g_nPickRetryCnt
    global g_flst_pick_up_Retry #add
    global g_Press_done

    buffer_idx = -1
    load_cell_pick_val = 0
    load_cell_normal_val = 0

    # Init nSeq, bStep
    nPreSeq = -10
    nSeq = -1
    bPreStep = False
    bStep = False

    indy_master.set_collision_level(4)

    indy_master.set_do(endtool_suction_idx, 0)
    indy_master.set_do(endtool_cylinder_idx, 0)
    indy_master.set_do(endtool_blow_idx, 0)


    # M000 = 0으로 초기화

    indy_master.write_direct_variable(10, 0, 0)


    # Environment_.ini에서 buffer_idx Read
    config.read(inipath)

    robot_pos = config.getint('robot_pos', 'buffer')  # 'robot_pos' 섹션의 'buffer' 키 값을 읽음.
 
    if 0 <= robot_pos < 3:
        if robot_pos == 0:
            conty_cmd(20)
        elif robot_pos == 1:
            conty_cmd(21)
        elif robot_pos == 2:
            conty_cmd(22)

        WriteRobotPosToIni(-1)
        print('complete comeback ready pos from buffer : ', robot_pos)

    elif robot_pos == 4:
        conty_cmd(23)

        WriteRobotPosToIni(-1)
        print('complete comeback ready pos from buffer : ', robot_pos)

    else:
        print('Not Escape robot_pos : ', robot_pos)
        pass

    # Init buffer_idx
    while True:
        print('BCD')
        time.sleep(0.01)
        dis = indy_master.get_di()
        buffer_fwd = [dis[4], dis[7], dis[10]]
        buffer_obj = [dis[5], dis[8], dis[11]]

        # 모든 Buffer에 소재가 없고, 전진 상태일 때 M030 = 1
        if buffer_obj[0] != sensor_on and buffer_fwd[0] == sensor_on and buffer_obj[1] != sensor_on and buffer_fwd[1] \
                == sensor_on and buffer_obj[2] != sensor_on and buffer_fwd[2] == sensor_on and nSeq == -1:
            indy_master.write_direct_variable(10, 30, 1)

        # buffer_empty_lamp_초기화, buffer_cylinder_down On
        for i in range(0, 3):
            if buffer_obj[i] != sensor_on:
                indy_master.set_do(i + 2, 1)
            elif buffer_obj[i] == sensor_on:
                indy_master.set_do(i + 2, 0)

            DoCylinderUp(i, False)  # add
            indy_master.set_do(buffer_blow_idx[i], 0)

        if (buffer_fwd[0] and buffer_obj[0]) == sensor_on:
            indy_master.set_do(2, 0)
            buffer_idx = 0
            break
        elif (buffer_fwd[1] and buffer_obj[1]) == sensor_on:
            indy_master.set_do(3, 0)
            buffer_idx = 1
            break
        elif (buffer_fwd[2] and buffer_obj[2]) == sensor_on:
            indy_master.set_do(4, 0)
            buffer_idx = 2
            break
        else:
            buffer_idx = -1

    print('buffer init Idx = ', buffer_idx)

    ###########################################################################################################
    # Start Sequence
    # M000 : 로봇 Motion 상태 값
    # M001 : 소재 Place 여부 상태 값
    # M030 : 로봇 일시정지
    ###########################################################################################################
    while 1:
        time.sleep(0.01)
        dis = indy_master.get_di()
        buffer_up = [dis[3], dis[6], dis[9]]  # buffer 상승 여부 감지 센서
        buffer_fwd = [dis[4], dis[7], dis[10]]  # buffer 전진 여부 감지 센서
        buffer_obj = [dis[5], dis[8], dis[11]]  # buffer 소재 여부 감지 센서
        button_auto = dis[12]  # Cycle Start
        button_stop = dis[13]  # Cycle Stop

        # bStepChanged = False

        if g_nPickRetryCnt > 3:
            indy_master.write_direct_variable(10, 30, 1)
            g_flst_pick_up_before.clear()
            g_nPickRetryCnt = 0
            nSeq = 0

        if nPreSeq != nSeq:
            nPreSeq = nSeq
            bStep = True
            # bStepChanged = True

        # elif bPreStep is not bStep:
            # bPreStep = bStep
            # bStepChanged = True

        # if bStepChanged is True:
            # print("Seq[%d] Step[%d]" % (nSeq, bStep))

        # buffer empty lamp on/off
        for i in range(0, 3):
            if buffer_obj[i] != sensor_on:
                indy_master.set_do(i + 2, 1)
            elif buffer_obj[i] == sensor_on:
                indy_master.set_do(i + 2, 0)

            if buffer_obj[i] == sensor_on and buffer_fwd[i] != sensor_on:
                print('buffer Back')
                indy_master.write_direct_variable(10, 30, 1)


        # if nSeq == -1 and buffer_obj[0] != sensor_on and buffer_fwd[0] == sensor_on and buffer_obj[1] != sensor_on \
        # and buffer_fwd[1] == sensor_on and buffer_obj[2] != sensor_on and buffer_fwd[2] == sensor_on:
        # print('not object')
        # robot1.write_direct_variable(10, 30, 1)

        if g_Press_done is True and indy_master.get_di()[15] == sensor_on:
            g_Press_done = False
            print('master_place_done = ', g_Press_done)

        if buffer_obj[0] != sensor_on and buffer_fwd[0] == sensor_on and buffer_obj[1] != sensor_on and \
                        buffer_fwd[1] == sensor_on and buffer_obj[2] != sensor_on and buffer_fwd[2] == sensor_on and nSeq == -1:
            indy_master.write_direct_variable(10, 30, 1)
            print('pause')

        # M030 == 1 : pause
        if indy_master.read_direct_variable(10, 30) == 1:
            continue

        # Cycle Start, Stop Switch
        if button_auto != sensor_on and nSeq == -1:
            indy_master.write_direct_variable(10, 30, 1)
            continue



        ###########################################################################################################
        # nSeq == -1 : Sequence 시작
        ###########################################################################################################
        if nSeq == -1:
            # M000 번지 Write/Read
            if bStep is True:
                if buffer_idx == 0 or 1 or 2:
                    indy_master.write_direct_variable(10, 0, 1)
                    bStep = False
                else:
                    indy_master.write_direct_variable(10, 0, 0)
                    nSeq = -1

            elif bStep is False:
                nSeq = 0



        ############################################################################################################
        # nSeq == 0
        # 소재 pick up 한 로봇 위치 값이 없으면 Seq 100, 없으면 Seq 150
        ############################################################################################################
        elif nSeq == 0:
            if not g_flst_pick_up_before:  # 이전 Pick Up 위치가 저장되어있지 않을 경우
                nSeq = 100
            else:  # Pick Up 위치가 저장되어 있을 경우
                nSeq = 150



        ############################################################################################################
        # nSeq == 100 : 이전에 소재를 Pick up한 로봇 위치 값이 없을 때 Sequence
        # bStep is True : Buffer 상단 위치(Pick Up Start)로 이동 후 소재를 안집었을 때 Load Cell 값 저장
        # bStep is False : 소재 감지될 때까지 하강 후 소재가 감지된 위치 값 저장
        ############################################################################################################
        elif nSeq == 100:
            if bStep is True:
                # buffer ready 위치 이동 로봇 상태 (M000 = 2)
                indy_master.write_direct_variable(10, 0, 2)

                # buff 레디 위치 이동
                if buffer_idx == 0:
                    conty_cmd(1)
                elif buffer_idx == 1:
                    conty_cmd(2)
                elif buffer_idx == 2:
                    conty_cmd(3)

                WriteRobotPosToIni(buffer_idx)
                
                time.sleep(0.5)
                load_cell_normal_val = indy_master.get_ai()[load_cell_idx]
                print('load_cell_normal_val : ', load_cell_normal_val)
                bStep = False
            else:
                # 충돌감도 Off
                collision_level = indy_master.get_collision_level()  # 기본 적용된 충돌 감도를 collision_level에 저장
                indy_master.set_collision_level(6)
                nSeq = 105


        elif nSeq == 105:
            if bStep is True:

                # buff 픽 위치 이동
                # stop motion 이 실행되면 실행중이던 모션 정지, 다음 커맨드 실행

                if buffer_idx == 0:
                    indy_master.write_direct_variable(0, COMMANDER_ADDR, 4)
                elif buffer_idx == 1:
                    indy_master.write_direct_variable(0, COMMANDER_ADDR, 5)
                elif buffer_idx == 2:
                    indy_master.write_direct_variable(0, COMMANDER_ADDR, 6)

                time.sleep(0.1)
                reach_end = False
                while not indy_master.get_di()[endtool_sensor_idx]:
                    time.sleep(0.01)
                    if indy_master.read_direct_variable(0, COMMANDER_ADDR) == 0:
                        reach_end = True
                        break
                
                if not reach_end:
                    indy_master.stop_motion()

                bStep = False

            else:
                pick_pos = indy_master.get_task_pos()
                g_flst_pick_up_before = indy_master.get_task_pos()
                nSeq = 110


        ############################################################################################################
        # nSeq == 110 : Pick Up 후 Buffer 상단 위치(Pick Up Start)로 상승하는 Sequence
        # bStep is True : 소재 감지된 위치에서 일정 거리만큼 상승 후 Picker Blow, 이 후 진공 켜서 소재 Pick-up 후 상승
        # bStep is False : Buffer 상단 위치(Pick Up Start)로 상승 후 Load Cell 값 저장
        ############################################################################################################
        elif nSeq == 110:
            if bStep is True:

                # z축 5mm 상대위치 이동
                conty_cmd(7) # up z 5 mm
                indy_master.set_do(endtool_blow_idx, 1)

                indy_master.task_move_to(g_flst_pick_up_before)
                
                indy_master.set_do(endtool_suction_idx, 1)
                indy_master.set_do(buffer_blow_idx[buffer_idx], 1)
                
                # buff 레디 위치 frame 이동
                if buffer_idx == 0:
                    conty_cmd(8)
                elif buffer_idx == 1:
                    conty_cmd(9)
                elif buffer_idx == 2:
                    conty_cmd(10)
                
                indy_master.set_collision_level(collision_level)
                bStep = False

            else:
                time.sleep(0.5)
                load_cell_pick_val = indy_master.get_ai()[load_cell_idx]
                print('load_cell_pick_vel : ', load_cell_pick_val)
                nSeq = 120

        ############################################################################################################
        # nSeq == 120 : Pick Up 여부를 확인하는 Sequence
        # bStep is True : 소재를 Pick Up 성공했을 때, 실패했을 때 처리
        # bStep is False : 소재를 Pick Up 성공했을 시, 소재가 2매 이상 감지 여부에 따라 처리
        ############################################################################################################
        elif nSeq == 120:
            if bStep is True:
                # dis = indy_master.get_di()  # indy의 Digital Input 신호를 dis 리스트에 저장
                # buffer_up = [dis[3], dis[6], dis[9]]  # buffer up 변수에 buffer up 여부를 확인하는 DI 신호를 저장(실린더 Up 센서)
                # buffer_obj = [dis[5], dis[8], dis[11]]  # buffer_obj 변수에 소재 여부를 감지하는 DI 신호를 저장(소재 감지 센서)

                if dis[endtool_sensor_idx] == sensor_on:  # Picker의 센서가 감지가 되었으면 아래 구문 진행
                    # Pick Up 완료 상태 (M000 = 3)
                    indy_master.write_direct_variable(10, 0, 3)
                    WhenPickUpCompleteFunc(buffer_idx, pick_pos[2], buffer_up, buffer_obj)
                    g_nPickRetryCnt = 0
                    bStep = False

                else:  # Fail case: re or cylinder up
                    if True == RetryToPickupfunc(buffer_idx, pick_pos[2], buffer_up):
                        g_nPickRetryCnt += 1
                        print('Pick Retry', g_nPickRetryCnt)
                        nSeq = 100
                    else:
                        nSeq = 0

            else:
                # 소재가 2장 이상 Pick 되었을 때 처리 nSeq = 200
                stdval = indy_master.read_direct_variable(10, 21)
                if (load_cell_pick_val - load_cell_normal_val) > stdval:
                    nSeq = 200

                else:
                    indy_master.set_do(buffer_blow_idx[buffer_idx], 0)
                    indy_master.set_do(endtool_blow_idx, 0)
                    nSeq = 250



        ############################################################################################################
        # nSeq == 150 : 이전에 소재를 Pick up한 로봇 위치 값이 있을 때
        # bStep is True : Buffer 상단 위치(Pick Up Start)로 이동 후 소재를 안집었을 때 Load Cell 값 저장
        # bStep is False : 이전에 Pick Up한 위치 값을 연산하여 이동.
        ############################################################################################################
        elif nSeq == 150:
            if bStep is True:
                # buffer ready 위치 이동 상태 (M000 = 2)
                indy_master.write_direct_variable(10, 0, 2)

                # buff 레디 위치 이동
                if buffer_idx == 0:
                    conty_cmd(1)
                elif buffer_idx == 1:
                    conty_cmd(2)
                elif buffer_idx == 2:
                    conty_cmd(3)

                # 소재를 집지 않았을 때 Load Cell 값 저장
                load_cell_normal_val = indy_master.get_ai()[load_cell_idx]
                time.sleep(0.5)
                bStep = False
            else:
                collision_level = indy_master.get_collision_level()
                indy_master.set_collision_level(6)
                nSeq = 155

        elif nSeq == 155:
            if bStep is True:
                downoffset = indy_master.read_direct_variable(10, 20) * 0.0001
                bStep = False
            else:
                if g_nPickRetryCnt > 0:
                    g_flst_pick_up_before = MoveOffset(downoffset, g_flst_pick_up_Retry)
                else:
                    g_flst_pick_up_before = MoveOffset(downoffset, g_flst_pick_up_before)  # 100.5
                nSeq = 160



        ############################################################################################################
        # nSeq == 160 : 소재 Pick Up 및 Load Cell 값 저장
        # bStep is True : Seq 150에서 Offset 값 만큼 하강한 위치에서 Picker Blow On, 일정 거리만큼 하강 후 소재 Pick Up
        # bStep is False : Buffer 상단 위치(Pick Up Start)로 상승 후 Load Cell 값 저장
        ############################################################################################################

        elif nSeq == 160:
            if bStep is True:
                indy_master.set_do(endtool_blow_idx, 1)

                indy_master.set_task_vel_level(1)
                conty_cmd(11) #z축 5 mm 하강

                indy_master.set_do(buffer_blow_idx[buffer_idx], 1)
                indy_master.set_do(endtool_suction_idx, 1)

                # buff start 위치 frame 이동
                if buffer_idx == 0:
                    conty_cmd(8)
                elif buffer_idx == 1:
                    conty_cmd(9)
                elif buffer_idx == 2:
                    conty_cmd(10)

                indy_master.set_collision_level(collision_level)
                bStep = False

            else:
                time.sleep(0.5)
                load_cell_pick_val = indy_master.get_ai()[load_cell_idx]
                print(load_cell_pick_val)
                nSeq = 170

        ############################################################################################################
        # Seq == 170 : Pick Up 여부를 확인하는 Sequence
        # bStep is True : 소재를 Pick Up 성공했을 때, 실패했을 때 처리
        # bStep is False : 소재를 Pick Up 성공했을 시, 소재가 2매 이상 감지 여부에 따라 처리
        ############################################################################################################
        elif nSeq == 170:
            if bStep is True:
                if dis[endtool_sensor_idx] == sensor_on:  # Picker의 센서가 감지가 되었으면 아래 구문 진행
                    # Pick Up 완료 상태 (M000 = 3)
                    indy_master.write_direct_variable(10, 0, 3)  # Pick Up 완료 상태
                    WhenPickUpCompleteFunc(buffer_idx, pick_pos[2], buffer_up, buffer_obj)
                    g_nPickRetryCnt = 0
                    bStep = False

                else:  # Fail case: re or cylinder up
                    if True == RetryToPickupfunc(buffer_idx, pick_pos[2], buffer_up):
                        g_nPickRetryCnt += 1
                        nSeq = 150
                    else:
                        nSeq = 0

            else:
                stdval = indy_master.read_direct_variable(10, 21)
                if (load_cell_pick_val - load_cell_normal_val) > stdval:
                    print('pick over 2 piece')
                    nSeq = 200

                else:
                    indy_master.set_do(buffer_blow_idx[buffer_idx], 0)
                    indy_master.set_do(endtool_blow_idx, 0)
                    nSeq = 250


        ###############################################################################################################
        # nSeq == 200 : 2매 이상 감지 시 Sequence
        # bStep is True : 정해진 횟수만큼 소재 분리 시도, 분리되었을 시 bStep = False. 분리가 되지 않으면 배출 위치에 배출.
        # bStep is False : 소재가 분리되면 Seq 250으로 넘어감
        ###############################################################################################################
        elif nSeq == 200:
            if bStep is True:
                nSeperateRetryCnt = 0
                indy_master.stop_motion()

                while 1:
                    val = indy_master.get_ai()[load_cell_idx]
                    # if (load_cell_pick_val - 100) > val > 200:
                    if stdval > val > 100:
                        print('seperate')
                        indy_master.set_do(buffer_blow_idx[buffer_idx], 0)
                        indy_master.set_do(endtool_blow_idx, 0)
                        bStep = False
                        break

                    if nSeperateRetryCnt < 3:
                        conty_cmd(12) # z 축 8 mm 하강
                        
                        # buff start 위치 frame 이동
                        if buffer_idx == 0:
                            conty_cmd(8)
                        elif buffer_idx == 1:
                            conty_cmd(9)
                        elif buffer_idx == 2:
                            conty_cmd(10)

                        nSeperateRetryCnt += 1

                    elif nSeperateRetryCnt >= 3:
                        print('Retry Count Over')
                        indy_master.set_do(buffer_blow_idx[buffer_idx], 0)

                        # pass point move
                        conty_cmd(13)

                        indy_master.set_do(endtool_suction_idx, 0)  # Picker의 진공 Off
                        indy_master.set_do(endtool_blow_idx, 0)
                        time.sleep(0.3)  # 0.3초 대기
                        
                        conty_cmd(14)
                        
                        nSeq = 450
                        break

            elif bStep is False:
                nSeq = 250



        ###############################################################################################################
        # nSeq == 250 : buffer에서 소재를 집은 후 Place 전 대기 위치
        # bStep is True : Place 대기 위치로 이동
        # bStep is False : M001 = 0 이고, Press Up 센서가 켜져있고, g_Press_done이 False이면 다음 Seq로 이동
        ###############################################################################################################
        elif nSeq == 250:
            if bStep is True:
                
                conty_cmd(15)
                WriteRobotPosToIni(4)  # Environment.ini 파일에 place 상태 기록

                time.sleep(0.01)
                indy_master.write_direct_variable(10, 0, 4)
                bStep = False

            elif bStep is False:
                if indy_master.read_direct_variable(10, 1) == 0 and indy_master.get_di()[15] == sensor_on and g_Press_done is False:
                    nSeq = 300


        ###############################################################################################################
        # nSeq == 300 : Press로 Place 하는 Sequence
        # bStep is True : Place 위치로 이동
        # bStep is False : -
        ###############################################################################################################
        elif nSeq == 300:
            if bStep is True:
                print('nSeq = 300, bStep = True')
                indy_master.set_joint_vel_level(joint_vel)

                # 블랜딩 추가 코드

                # Place 위치 이동
                indy_master.write_direct_variable(10, 0, 5)
                indy_master.set_do(endtool_cylinder_idx, 1)

                conty_cmd(16) # move

                indy_master.set_do(endtool_suction_idx, 0)
                time.sleep(0.2)

                # Place 완료 상태(M000 = 6)
                indy_master.write_direct_variable(10, 0, 6)

                time.sleep(0.01)
                bStep = False

            elif bStep is False:
                print('nSeq = 300, bStep = False')
                nSeq = 350


        ###############################################################################################################
        # nSeq == 350 : 소재 Place 후 복귀 Sequence
        # bStep is True : 소재 Place 후 복귀
        # bStep is False : -
        ###############################################################################################################
        elif nSeq == 350:
            if bStep is True:
                print('nSeq = 350, bStep = True')

                conty_cmd(17)
                print('Up End')
                
                indy_master.set_do(endtool_cylinder_idx, 0)
                conty_cmd(18)
                # Place 위치에서 빠져나옴 ( M000 = 7 )
                # indy_master.write_direct_variable(10, 0, 7)  # M000 = 7

                WriteRobotPosToIni(4)
                
                time.sleep(0.01)
                bStep = False

            elif bStep is False:
                print('nSeq = 350, bStep = False')
                nSeq = 400


        ###############################################################################################################
        # nSeq == 400 : Press 동작 Sequence
        # bStep is True : Press Up 센서가 켜져있으면 ( Press가 Up 상태이면 ) Press 동작
        # bStep is False : Press Up 센서가 꺼져있으면 ( Press가 Down 상태이면 ) M001 = 1, Ready 위치 복귀
        ###############################################################################################################
        elif nSeq == 400:
            if bStep is True:
                if indy_master.get_di()[15] == sensor_on:
                    print('nSeq = 400, bStep = True')
                    DoPressOn(True)
                    bStep = False
                    print('bStep = False')

            elif bStep is False:
                if indy_master.get_di()[15] == sensor_off:
                    print('nSeq = 400, bStep = False')
                    indy_master.write_direct_variable(10, 1, 1)
                    conty_cmd(19) # move pass point
                    
                    indy_master.write_direct_variable(10, 0, 7)  # M000 = 7
                    WriteRobotPosToIni(-1)
                    #indy_master.write_direct_variable(10, 0, 0)
                    g_Press_done = True
                    nSeq = 450


        ###############################################################################################################
        # nSeq == 450 : Buffer 소재 Check 및 buffer idx 전환 Sequencd
        # bStep is True : Buffer에 소재 여부 Check. 기존 Pick Up 한 Buffer에 소재가 있으면 buffer_idx 유지. 없으면 다음 buffer_idx로 전환
        # bStep is False : Seq -1로 복귀
        ###############################################################################################################
        elif nSeq == 450:
            if bStep is True:
                print('nSeq = 450, bStep = True')
                if buffer_idx == 0:
                    if (buffer_fwd[0] and buffer_obj[0]) == sensor_on:
                        bStep = False
                    #elif (buffer_fwd[0] and buffer_obj[0]) != sensor_on:
                    elif buffer_obj[0] != sensor_on:
                        g_flst_pick_up_before.clear()
                        buffer_idx = 1

                elif buffer_idx == 1:
                    if (buffer_fwd[1] and buffer_obj[1]) == sensor_on:
                        bStep = False
                    #elif (buffer_fwd[1] and buffer_obj[1]) != sensor_on:
                    elif buffer_obj[1] != sensor_on:
                        g_flst_pick_up_before.clear()
                        buffer_idx = 2

                elif buffer_idx == 2:
                    if (buffer_fwd[2] and buffer_obj[2]) == sensor_on:
                        bStep = False
                    #elif (buffer_fwd[2] and buffer_obj[2]) != sensor_on:
                    elif buffer_obj[2] != sensor_on:
                        g_flst_pick_up_before.clear()
                        buffer_idx = 0

                if buffer_obj[0] != sensor_on and buffer_fwd[0] == sensor_on and buffer_obj[1] != sensor_on and \
                        buffer_fwd[1] == sensor_on and buffer_obj[2] != sensor_on and buffer_fwd[2] == sensor_on:
                    indy_master.write_direct_variable(10, 30, 1)
                    print('nSeq450,True,Pause')
                    

            elif bStep is False:
                print('nSeq = 450, bStep = False')
                nSeq = -1


#################################################################################################################
#####################                      define functions                          ############################

def DoPressOn(bSet):
    indy_master.set_do(Press_on_idx, bSet)
    time.sleep(0.08)
    indy_master.set_do(Press_on_idx, not bSet)


def WhenPickUpCompleteFunc(nIdx_buf, pick_PosZ, buffer_up, buffer_obj): #bHaveBefPos):
    # global g_nPickRetryCnt
    # g_nPickRetryCnt = 0

    if buffer_obj[nIdx_buf] == sensor_on:  # buffer_idx에 소재가 감지 되었으면 아래 구문 진행
        # pick_pos[2] = pick_pos의 Z축 위치 값이 buffer_z_threshold 값보다 작고 buffer가 up되지 않으면
        if pick_PosZ < buffer_z_threshold[nIdx_buf] and not buffer_up[nIdx_buf]:
            DoCylinderUp(nIdx_buf, True)
            indy_master.set_do(buffer_blow_idx[nIdx_buf], 0)
            CheckBufCylUp(nIdx_buf)  # 실린더 Up 센서가 ON(1)이 아니면 대기한다. ON(1)이 되면 while 문을 빠져나옴.

            # if bHaveBefPos is True:  # Seq 15
            g_flst_pick_up_before.clear()

    else:  # buffer에 소재가 감지되지 않으면
        #if bHaveBefPos is False:  # Seq10
        g_flst_pick_up_before.clear()
        if buffer_up[nIdx_buf]:  # buffer가 Up 되어있으면
            DoCylinderUp(nIdx_buf, False)


def RetryToPickupfunc(nIdx_buf, pick_PosZ, buffer_up):
    if buffer_up[nIdx_buf] == sensor_on:
        print("Re")
        #g_flst_pick_up_before.clear()
        #g_nPickRetryCnt += 1
        bRetry = True
    else:
        if pick_PosZ < buffer_z_threshold[nIdx_buf]:
            print("Cylinder up --> Re")
            DoCylinderUp(nIdx_buf, True)
            indy_master.set_do(buffer_blow_idx[nIdx_buf], 0)
            g_flst_pick_up_before.clear()
            CheckBufCylUp(nIdx_buf)  # 실린더 Up 센서가 ON(1)이 아니면 대기한다. ON(1)이 되면 while 문을 빠져나옴.
            # nSeq = 0
            bRetry = False
        else:
            print("Re")
            # g_flst_pick_up_before.clear()
            # g_nPickRetryCnt += 1
            # nSeq = 0
            bRetry = True

    return bRetry



def CheckBufCylUp(nIdx_buf):
    while not indy_master.get_di()[cylinder_up_sensor[nIdx_buf]]:
        # 실린더 Up 센서가 ON(1)이 아니면 대기한다. ON(1)이 되면 while 문을 빠져나옴.
        if cylinder_up_sensor[nIdx_buf]:
            time.sleep(0.01)
    time.sleep(0.1)  # 0.1초 대기

def MoveOffset(fdownoffset, flst_Pickup_bef_Pos):
    global g_flst_pick_up_Retry
    g_flst_pick_up_Retry = flst_Pickup_bef_Pos                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      

    postmp1 = flst_Pickup_bef_Pos
    postmp2 = [0, 0, -fdownoffset, 0, 0, 0]
    postmp3 = []
    postmp4 = [0, 0, 0.050, 0, 0, 0]
    postmp5 = []

    for a, b in zip(postmp1, postmp2):
        postmp3.append(a + b)

    flst_Pickup_bef_Pos = postmp3  # 이전 pick-up위치에 downoffset값 만큼 내려간 값을 pick_up_before에 저장
    print('pick up pos = ', flst_Pickup_bef_Pos)

    for a, b in zip(postmp3, postmp4):
        postmp5.append(a + b)
    
    indy_master.task_move_to(postmp5)

    return flst_Pickup_bef_Pos


def WriteRobotPosToIni(nBufIdx):
    config.set('robot_pos', 'buffer', str(nBufIdx))
    with open(inipath, 'r+') as Envfile:
        config.write(Envfile)
        os.sync()


def DoCylinderUp(nBufIdx, bSet):
    indy_master.set_do(cylinder_up_idx[nBufIdx], bSet)
    indy_master.set_do(cylinder_down_idx[nBufIdx], not bSet)


def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    print("Disconnected")
    sys.exit(-1)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    main()
