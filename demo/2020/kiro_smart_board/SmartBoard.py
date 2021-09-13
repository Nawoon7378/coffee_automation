if __name__ == "__main__":
    print("Not supported as a main script.")
    exit(-1)

from indy_utils import indydcp_client as dcp_client, indyeye_client as eye_client
from indy_utils.indy_program_maker import JsonProgramComponent
import Logger as L

import json
import threading
from time import sleep

import socket
import math
import pickle
import numpy as np

from weather_caster import weather_caster

# Direct variables for IndyHand
DIRECT_VAR_TYPE_BYTE       = 0   # 1 Byte unsigned integer (0-255)
DIRECT_VAR_TYPE_WORD       = 1   # 2 Byte integer (-32768 - 32767)
DIRECT_VAR_TYPE_DWORD      = 2   # 4 Byte integer (-2,147,483,648 - 2,147,483,647)
DIRECT_VAR_TYPE_LWORD      = 3   # 8 Byte integer (-9223372036854775808 to 9223372032559808511)
DIRECT_VAR_TYPE_FLOAT      = 4   # 4 Byte floating number
DIRECT_VAR_TYPE_DFLOAT     = 5   # 8 Byte floating number
DIRECT_VAR_TYPE_MODBUS_REG = 10  # ModbusTCP, 2 Byte unsigned integer (0 - 65535)

# Global variables for IndyHand
IH_HOLD_TYPE                = 1
IH_HOLD_FORCE               = 70
IH_HOLD_ADDRESS_OF_TYPE     = 101
IH_HOLD_ADDRESS_OF_FORCE    = 102
IH_OPEN_TYPE                = 1
IH_OPEN_RANGE               = 1
IH_OPEN_ADDRESS_OF_TYPE     = 201
IH_OPEN_ADDRESS_OF_RANGE    = 202

# Global variables for base data
BASE_DATA_CONFIG_PATH = "/home/user/release/SmartBoard/config.json"
BASE_DATA_KEY_BOARD_SEED_POSE = "board_seed_pose"
BASE_DATA_KEY_BOARD_POSE_INTERVAL = "board_pose_interval"
BASE_DATA_KEY_BOARD_PICK_RELATIVE_POSITION = "board_pick_relative_position"
BASE_DATA_KEY_HAND_TOOL_POSITION_ON_VIEW = "indyhand_tool_position_on_view"
BASE_DATA_KEY_HAND_TOOL_POSITION_ON_BOARD = "indyhand_tool_position_on_board"
BASE_DATA_KEY_SHEET_DETECT_POSITION = "sheet_detect_position"
BASE_DATA_KEY_SHEET_RELATED_DISTANCE = "sheet_related_distance"
BASE_DATA_KEY_EYE_DETECTION_POSES = "eye_detection_poses"

# Global variables for this module
MSG_BTN_GREEN   = 1
MSG_BTN_BLUE    = 2
MSG_BTN_YELLOW  = 3
MSG_BTN_RED     = 4

IP_ADDRESS_DCP = "172.16.201.165"
IP_ADDRESS_EYE = "172.16.201.164"
name = "NRMK-Indy7"
indy = dcp_client.IndyDCPClient(IP_ADDRESS_DCP, name)
eye = eye_client.IndyEyeClient(IP_ADDRESS_EYE)
forecaster = weather_caster()
base_data = None
DCP_TIMEOUT = 3

IS_PROCESSING = False
IS_EMERGENCY = False
IS_FORECASTING = False
PREV_FORECAST_RESULT = None
forecasting_thread = None

called_threads = []
thread_lock = threading.Lock()

# DCP timeout connector
def connect_DCP(indy, timeout=3):
    global base_data
    indy.sock_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    indy.sock_fd.settimeout(timeout)
    base_data = load_config()
    try:
        indy.sock_fd.connect((indy.server_ip, 6066))
    except socket.error as e:
        L.err("Socket connection error: {}".format(e))
        indy.sock_fd.close()
        return False
    else:
        L.info("DCP Connect: Server IP ({ser_ip})".format(ser_ip=indy.server_ip))
        return True

############################################################################################
### Implements begin ▼
############################################################################################

# Main event listener
def client_attached(addr):
    global indy, DCP_TIMEOUT, base_data
    connect_DCP(indy, DCP_TIMEOUT)
    L.info("The client was attached.")

def client_detached():
    global indy, DCP_TIMEOUT
    indy.disconnect()
    L.info("The client was detached.")

def btn_green_pressed():
    global PREV_FORECAST_RESULT
    weathers, pms, _ = forecaster.get_forecasts()
    pairs = [ (weathers[idx], pm_to_state(pms[idx])) for idx in range(len(weathers)) ]
    for idx, pair in enumerate(pairs):
        exec_detecting(eye, base_data, idx, 1, 1, pair[0])
        exec_detecting(eye, base_data, idx, 0, 4, pair[1])
        go_home()
    PREV_FORECAST_RESULT = pairs

def btn_blue_pressed():
    global IS_FORECASTING, PREV_FORECAST_RESULT
    def forecasting():
        global IS_FORECASTING, PREV_FORECAST_RESULT, IS_EMERGENCY
        IS_FORECASTING = True
        while IS_FORECASTING and not IS_EMERGENCY:
            weathers, pms, _ = forecaster.get_forecasts()
            pairs = [ (weathers[idx], pm_to_state(pms[idx])) for idx in range(len(weathers)) ]
            L.err("{}, {}".format(PREV_FORECAST_RESULT, pairs))
            for idx, pair in enumerate(pairs):
                prev_pair = PREV_FORECAST_RESULT[idx]
                if prev_pair[0] != pair[0]:
                    exec_detecting(eye, base_data, idx, 1, 1, pair[0])
                if prev_pair[1] != pair[1]:
                    exec_detecting(eye, base_data, idx, 0, 4, pair[1])
                if idx == len(pair) - 1:
                    go_home()
            PREV_FORECAST_RESULT = pairs
            sleep(1)
        IS_FORECASTING = False
    if IS_FORECASTING:
        IS_FORECASTING = False
        forecasting_thread.join()
        forecasting_thread = None
    else:
        btn_green_pressed()
        forecasting_thread = threading.Thread(target=forecasting, daemon=True)
        forecasting_thread.start()

def btn_yellow_pressed():
    L.info("YELLOW")
    teach_board_from_sheet(eye, base_data)

def btn_red_pressed():
    global IS_EMERGENCY
    L.info("RED")
    IS_EMERGENCY = True

    thread_lock.acquire()
    try:
        for thread in called_threads:
            try:
                while thread.is_alive():
                    indy.stop_motion()
                    indy.stop_current_program()
                    sleep(0.1)
            except:
                pass
    finally:
        thread_lock.release()
    
    IS_EMERGENCY = False

def exec_detecting(eye, base_data, x, y, tool_type, target):
    callback_result = {}
    pnp_on_board(base_data, x, y, tool_type, True)
    not_detected = True
    tried_count = 0
    while not_detected and tried_count < 5 and not IS_EMERGENCY:
        detect_sequence(eye, base_data, tool_type, 'empty_position', False, False, callback_result)
        if 'pose' in callback_result.keys() and callback_result['pose'] is not None:
            not_detected = False
            tried_count = 0
        else:
            tried_count += 1
    
    if not_detected:
        return
    
    not_detected = True
    tried_count = 0
    while not_detected and tried_count < 5 and not IS_EMERGENCY:
        detect_sequence(eye, base_data, tool_type, target, True, True, callback_result)
        if 'pose' in callback_result.keys() and callback_result['pose'] is not None:
            pnp_on_board(base_data, x, y, tool_type, False)
            not_detected = False
            tried_count = 0
        else:
            tried_count += 1

############################################################################################
### Implements end ▲
############################################################################################

# Program Maker Component Decorator
def json_program(client, policy=0, resume_time=2, wait_for_finish=True):
    def decorate(func):
        def decorated(*args):
            if IS_EMERGENCY:
                return
            prog = JsonProgramComponent(policy=policy, resume_time=resume_time)
            func(prog, *args)
            client.set_and_start_json_program(prog.program_done()) # Execute program
            if wait_for_finish:
                client.wait_for_program_finish()
        return decorated
    return decorate

def json_loop_program(client, policy=0, resume_time=2, wait_for_finish=True):
    def decorate(func):
        def decorated(*args):
            if IS_EMERGENCY:
                return
            result = True
            loop_cnt = 0
            while result is True:
                if IS_EMERGENCY:
                    return
                wait_flag = wait_for_finish
                prog = JsonProgramComponent(policy=policy, resume_time=resume_time)
                result = func(client, prog, loop_cnt, *args)
                if type(result) is tuple:
                    result, wait_flag = result
                client.set_and_start_json_program(prog.program_done()) # Execute program
                if wait_flag:
                    client.wait_for_program_finish()
                loop_cnt += 1
        return decorated
    return decorate

def load_config():
    global BASE_DATA_CONFIG_PATH
    try:
        with open(BASE_DATA_CONFIG_PATH, 'r') as f:
            data = json.load(f)
            f.close()
    except:
        data = None
    return data

def save_config(obj):
    global BASE_DATA_CONFIG_PATH
    with open(BASE_DATA_CONFIG_PATH, 'w') as f:
        json.dump(obj, f, indent=4, sort_keys=True)
        f.close()

def detect_obj(indy, eye, obj_tag):
    objs = eye.get_object_dict()
    found_target = None
    found_target_idx = -1
    for key in objs.keys():
        print(obj_tag, key, objs)
        if obj_tag in objs[key]:
            found_target = objs[key]
            found_target_idx = int(key)
    if found_target_idx != -1:
        result = eye._run_command(cmd=0, cls=found_target_idx, pose_cmd=indy.get_task_pos())
        if result['class_detect'] == found_target_idx:
            found_target = result['Tbo']
        else:
            found_target = None
    return found_target

def pm_to_state(pm):
    pm_cut = 35
    return "good" if pm < pm_cut else "bad"

# Teaching function via calibration sheet
@json_loop_program(indy)
def teach_board_from_sheet(indy, prog, loop_cnt, eye, base_data):
    if loop_cnt == 0:
        prog.add_move_home()
        prog.add_task_move_to(base_data[BASE_DATA_KEY_SHEET_DETECT_POSITION], vel=0)
    elif loop_cnt == 1:
        open_hand(indy, 4)
        sleep(2)
        hold_hand(indy, 4)
        sleep(2)
        sheet_pos = detect_obj(indy, eye, "sheet")
        if sheet_pos is None:
            return False, False
        base_data[BASE_DATA_KEY_BOARD_SEED_POSE] = list(np.asarray(sheet_pos) + base_data[BASE_DATA_KEY_SHEET_RELATED_DISTANCE])
        save_config(base_data)
    elif loop_cnt == 2:
        open_hand(indy, 1)
        sleep(2)
        hold_hand(indy, 1)
        sleep(2)
        pnp_on_board(base_data, 0, 0, 1, True)
    return loop_cnt < 2

@json_loop_program(indy)
def pnp_on_board(indy, prog, loop_cnt, base_data, x, y, tool_type, is_picking):
    seed_pos = base_data[BASE_DATA_KEY_BOARD_SEED_POSE]
    rel_task = base_data[BASE_DATA_KEY_BOARD_PICK_RELATIVE_POSITION]
    interval = base_data[BASE_DATA_KEY_BOARD_POSE_INTERVAL]
    tool_pose = base_data[BASE_DATA_KEY_HAND_TOOL_POSITION_ON_BOARD]["weather" if tool_type == 1 else "pm"]
    if loop_cnt == 0:
        x = x % 3
        y = y % 2
        ready_pos = np.asarray(seed_pos)
        rel_interval = np.asarray([y, x, y, 0, 0, 0]) * interval
        ready_pos += rel_interval
        ready_pos += tool_pose
        prog.add_task_move_to(list(ready_pos))
    elif loop_cnt == 1:
        if is_picking:
            open_hand(indy, tool_type)
    elif loop_cnt == 2:
        prog.add_task_move_by(rel_task)
    elif loop_cnt == 3:
        if is_picking:
            hold_hand(indy, tool_type)
            if tool_type == 1:
                sleep(2)
        else:
            open_hand(indy, tool_type)
    elif loop_cnt == 4:
        prog.add_task_move_by(list(-np.asarray(rel_task)))
    return loop_cnt < 4

@json_loop_program(indy)
def detect_sequence(indy, prog, loop_cnt, eye, base_data, tool_type, target, is_picking, move_to_home, result):
    detect_poses = base_data[BASE_DATA_KEY_EYE_DETECTION_POSES]
    seq_cnt = 4
    idx = int(loop_cnt / seq_cnt)
    seq_idx = loop_cnt % seq_cnt
    keep_running_flag = True
    tool_pose = base_data[BASE_DATA_KEY_HAND_TOOL_POSITION_ON_VIEW]["weather" if tool_type == 1 else "pm"][idx]
    if idx >= len(detect_poses):
        return False
    detect_pose = detect_poses[idx]
    wait_for_finish = False
    if seq_idx == 0:
        prog.add_task_move_to(detect_pose)
        wait_for_finish = True
    elif seq_idx == 1:
        found_pos = detect_obj(indy, eye, target)
        if found_pos is not None and not math.isnan(found_pos[0]):
            result['pose'] = found_pos
            wait_for_finish = True
        else:
            result['pose'] = None
    elif seq_idx == 2 and result['pose'] is not None:
        pose = result['pose'].copy()
        ready_pose = detect_pose.copy()
        ready_pose[0] = pose[0] + tool_pose[0]
        ready_pose[1] = pose[1] + tool_pose[1]
        # ready_pose[5] += pose[5]
        prog.add_task_move_to(ready_pose, vel=3)
        obj_pose = ready_pose.copy()
        obj_pose[2] = pose[2] + tool_pose[2]
        print(pose)
        if is_picking:
            open_hand(indy, tool_type)
            sleep(2)
        else:
            obj_pose[2] += 0.002
        prog.add_task_move_to(obj_pose, vel=0)
        wait_for_finish = True
    elif seq_idx == 3 and result['pose'] is not None:
        pose = result['pose'].copy()
        ready_pose = detect_pose.copy()
        ready_pose[0] = pose[0] + tool_pose[0]
        ready_pose[1] = pose[1] + tool_pose[1]
        ready_pose[2] = pose[2] + tool_pose[2] + 0.05
        # ready_pose[5] += pose[5]
        prog.add_task_move_to(ready_pose, vel=0)
        keep_running_flag = False

        if is_picking:
            hold_hand(indy, tool_type)
            sleep(1)
        else:
            open_hand(indy, tool_type)
        sleep(1)
        if move_to_home:
            prog.add_move_home()
        wait_for_finish = True
        
    return keep_running_flag, wait_for_finish

@json_program(indy)
def go_home(prog):
    prog.add_move_home()

# IndyHand functions
def hold_hand(indy,
    hold_type=IH_HOLD_TYPE,
    force=IH_HOLD_FORCE,
    type_addr=IH_HOLD_ADDRESS_OF_TYPE,
    force_addr=IH_HOLD_ADDRESS_OF_FORCE):
    
    indy.write_direct_variable(dv_type=DIRECT_VAR_TYPE_BYTE, dv_addr=type_addr, val=hold_type)
    indy.write_direct_variable(dv_type=DIRECT_VAR_TYPE_BYTE, dv_addr=force_addr, val=force)

def open_hand(indy,
    open_type=IH_OPEN_TYPE,
    open_range=IH_OPEN_RANGE,
    type_addr=IH_OPEN_ADDRESS_OF_TYPE,
    range_addr=IH_OPEN_ADDRESS_OF_RANGE):
    
    indy.write_direct_variable(dv_type=DIRECT_VAR_TYPE_BYTE, dv_addr=type_addr, val=open_type)
    indy.write_direct_variable(dv_type=DIRECT_VAR_TYPE_BYTE, dv_addr=range_addr, val=open_range)

def read_hold_hand_variables(indy,
    type_addr=IH_HOLD_ADDRESS_OF_TYPE,
    force_addr=IH_HOLD_ADDRESS_OF_FORCE):
    return (
        indy.read_direct_variable(dv_type=DIRECT_VAR_TYPE_BYTE, dv_addr=IH_HOLD_ADDRESS_OF_TYPE),
        indy.read_direct_variable(dv_type=DIRECT_VAR_TYPE_BYTE, dv_addr=IH_HOLD_ADDRESS_OF_FORCE)
    )

def read_open_hand_variables(indy,
    type_addr=IH_OPEN_ADDRESS_OF_TYPE,
    range_addr=IH_OPEN_ADDRESS_OF_RANGE):
    return (
        indy.read_direct_variable(dv_type=DIRECT_VAR_TYPE_BYTE, dv_addr=IH_OPEN_ADDRESS_OF_TYPE),
        indy.read_direct_variable(dv_type=DIRECT_VAR_TYPE_BYTE, dv_addr=IH_OPEN_ADDRESS_OF_RANGE)
    )

def data_listener(msg_type, msg):
    global IS_PROCESSING, base_data
    L.info("Data Listener - Type : {}, msg : {}".format(msg_type, msg))
    base_data = load_config()

    if msg_type == 1:
        if 0 < msg < 5:
            if IS_PROCESSING and msg != MSG_BTN_RED:
                L.warn("Task is now running. Ignoring the request.")
                return
            
            # acquire thread
            cur_thread = threading.current_thread()
            thread_lock.acquire()
            try:
                called_threads.append(cur_thread)
            finally:
                thread_lock.release()
            
            # emergency button validation
            if msg != MSG_BTN_RED:
                IS_PROCESSING = True

            funcs = [
                btn_green_pressed,
                btn_blue_pressed,
                btn_yellow_pressed,
                btn_red_pressed
            ]

            # function call
            try:
                funcs[msg-1]()
            except:
                L.err("Task was terminated abnormally.")
            
            # end sequence
            if msg != MSG_BTN_RED:
                IS_PROCESSING = False

            # release thread
            thread_lock.acquire()
            try:
                called_threads.remove(cur_thread)
            finally:
                thread_lock.release()
    

# EOF