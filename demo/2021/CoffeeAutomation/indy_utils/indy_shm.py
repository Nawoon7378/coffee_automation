'''
Created on 2020. 3. 13.

@author: YJHeo
@author: GWKim
'''

import sys
from posix_ipc import SharedMemory
from os import read, write, lseek, SEEK_SET
from struct import pack, unpack
import math
import time
from threading import Lock
import os
import random
from .indy_shm_addr import *

# INDY_SHM_CLEINT_ADDR8_CMD_RETURN(CMD_ADDR) CMD_ADDR+0x20000	#0x410000~0x41FFFF
def cmd_return(cmd_addr):
    return cmd_addr + 0x20000

def rad2deg(x):
    return (x * 180) / math.pi


def deg2rad(x):
    return (x * math.pi) / 180.0


class ShmWrapper(object):
    def __init__(self, name, offset, size, flags=0):
        try:
            self.shm = SharedMemory(name, flags=flags)
        except:
            print("Share memory '%s' open error" % name)
            sys.exit(-1)
        self.offset = offset + INDY_SHM_MGR_OFFSET
        self.size = size
        # print("Shared Memory:", name, self.offset, size)

    def read(self):
        lseek(self.shm.fd, self.offset, SEEK_SET)
        return read(self.shm.fd, self.size)

    def write(self, data=None):
        lseek(self.shm.fd, self.offset, SEEK_SET)
        if data is None:
            return write(self.shm.fd, '1'.encode())
        else:
            return write(self.shm.fd, data)

    def close(self):
        self.shm.close_fd()


class IndyShmCommand:
    def __init__(self, sync_mode=True, joint_dof=6):
        self.joint_dof = joint_dof
        self.sync_mode = sync_mode
        self.lock = Lock()

    def shm_access(self, shm_name, data_size, data_type=''):
        # self.lock.acquire()
        shm = ShmWrapper(INDY_SHM_NAME, shm_name, data_size)
        if len(data_type) == 0:
            val = shm.read()
        else:
            val = list(unpack(data_type, shm.read()))
        if len(val) == 1:
            val = val[0]
        shm.close()
        # self.lock.release()
        return val

    def shm_command(self, shm_name, data_size=1, data_type='', shm_data=None):
        # self.lock.acquire()
        shm = ShmWrapper(INDY_SHM_NAME, shm_name, data_size)
        if len(data_type) == 0:
            ret = shm.write(shm_data)
        else:
            if type(shm_data) == list:
                ret = shm.write(pack(data_type, *shm_data))
            else:
                ret = shm.write(pack(data_type, shm_data))
        shm.close()
        # self.lock.release()
        return ret

    # Logic functions
    def command_set_logic(self, cmd_name, add_arg=None):
        if self.get_robot_status()['busy']:
            return False
        elif self.shm_access(cmd_name, 1) == 0:
            if add_arg is not None:
                self.shm_command(add_arg['cmd_name'], add_arg['cmd_size'], add_arg['data_type'], add_arg['data'])
            self.shm_command(cmd_name)

            while self.shm_access(cmd_name, 1):
                time.sleep(0.001)
            ret = self.shm_access(cmd_return(cmd_name), 1)
            # sem post
            return ret

        else:
            return False

    def command_motion_logic(self, cmd_name, add_arg=None):
        robot_state = self.get_robot_status()
        is_emg = robot_state['emergency']
        is_busy = robot_state['busy']

        if is_emg:
            print("Emg")
            return False

        if is_busy:
            if self.sync_mode:
                print("Sync - Busy")
                while self.get_robot_status()['busy']:
                    time.sleep(0.005)
            else:
                print("Async - Busy")
                return False

        while not self.shm_access(cmd_name, 1) == 0:
            time.sleep(0.001)

        if add_arg is not None:
            self.shm_command(add_arg['cmd_name'], add_arg['cmd_size'], add_arg['data_type'], add_arg['data'])

        self.shm_command(cmd_name)
        while self.shm_access(cmd_name, 1):
            time.sleep(0.001)

        while True:
            time.sleep(0.005)
            if self.get_robot_status()['busy']:
                break

        if self.sync_mode:
            while True:
                time.sleep(0.005)
                status = self.get_robot_status()
                if status['movedone'] and not status['busy']:
                    break
            return self.get_robot_status()['movedone']
        else:
            return True

    def command_program_logic(self, cmd_name):
        robot_state = self.get_robot_status()
        is_emg = robot_state['emergency']
        is_busy = robot_state['busy']

        if self.sync_mode:
            while is_emg:
                time.sleep(0.005)
        elif is_emg:
            return False

        if is_busy:
            return False
        elif self.shm_access(cmd_name, 1) == 0:
            # wait semaphore

            self.shm_command(cmd_name)
            while self.shm_access(cmd_name, 1):
                time.sleep(0.04)

            return self.shm_access(cmd_return(cmd_name), 1)
        else:
            return False

    def command_program_compact_logic(self, cmd_name, add_arg=None):
        if self.shm_access(cmd_name, 1) == 0:
            # wait semaphore
            if add_arg is not None:
                self.shm_command(add_arg['cmd_name'], add_arg['cmd_size'], add_arg['data_type'], add_arg['data'])
            self.shm_command(cmd_name)

            while self.shm_access(cmd_name, 1):
                time.sleep(0.001)
            return self.shm_access(cmd_return(cmd_name), 1)
        else:
            return False

    def command_program_pause_logic(self, cmd_name, add_arg=None):
        if self.shm_access(cmd_name, 1) == 0:
            # wait semaphore
            if add_arg is not None:
                self.shm_command(add_arg['cmd_name'], add_arg['cmd_size'], add_arg['data_type'], add_arg['data'])
            self.shm_command(cmd_name)

            while self.shm_access(cmd_name, 1):
                time.sleep(0.001)
            return self.shm_access(cmd_return(cmd_name), 1)
        else:
            return False

    def command_jogging_logic(self, cmd_name, add_arg):
        robot_state = self.get_robot_status()
        is_emg = robot_state['emergency']

        if self.sync_mode:
            while is_emg:
                time.sleep(0.005)
        elif is_emg:
            return False

        if self.shm_access(cmd_name, 1) == 0:
            self.shm_command(add_arg['cmd_name'], add_arg['cmd_size'], add_arg['data_type'], add_arg['data'])
            self.shm_command(cmd_name)
            return True
        else:
            return False

    # Robot control state
    def get_robot_status(self):
        attr = ['ready', 'emergency', 'collision', 'error', 'busy', 'movedone',
                'home', 'zero', 'resetting',   'teaching', 'direct_teaching']
        shm_val = self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_STATUS_STRUCT_DATA, 11)
        res = {}

        for att in attr:
            res[att] = bool(shm_val[attr.index(att)])
        return res

    # Program state
    def get_program_state(self):
        attr = ['program_mode', 'program_state']
        program_mode = ['no loaded', 'command', 'conty', 'script']
        program_state = ['stop', 'running', 'pause']
        shm_val = self.shm_access(INDY_SHM_ROBOT_ADDR_STATE_PROGRAM_MODE, 2)

        res = {attr[0]: program_mode[shm_val[attr.index(attr[0])]],
               attr[1]: program_state[shm_val[attr.index(attr[1])]]}
        return res

    # Reset/Stop
    def command_stop_logic(self, cmd_name):
        if self.get_robot_status()['emergency']:
            return
        self.shm_command(cmd_name)
        if self.sync_mode:
            while self.shm_access(cmd_name, 1):
                time.sleep(0.001)
            while self.get_robot_status()['busy']:
                time.sleep(0.001)

    def stop_motion(self):
        # > 300ms
        return self.command_stop_logic(INDY_SHM_CLIENT_ADDR8_CMD_STOP_SLOW)

    def stop_emergency(self):
        # < 10ms
        self.command_stop_logic(INDY_SHM_CLIENT_ADDR8_CMD_STOP_EMERGENCY)

    def stop_safe(self):
        # ~ 250ms
        self.command_stop_logic(INDY_SHM_CLIENT_ADDR8_CMD_STOP_SAFE)

    def reset_robot(self, hard_reset=False):
        if hard_reset:
            self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_RESET_HARD)
            if self.sync_mode:
                while self.shm_access(INDY_SHM_CLIENT_ADDR8_CMD_RESET_HARD, 1):
                    time.sleep(0.01)
                # sems post

        else:
            self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_RESET_SOFT)
            if self.sync_mode:
                while self.shm_access(INDY_SHM_CLIENT_ADDR8_CMD_RESET_SOFT, 1):
                    time.sleep(0.01)
                # sems post

    # Joint/Servo command

    # Direct teaching
    def command_set_no_busy_logic(self, cmd_name, add_arg=None):
        if self.shm_access(cmd_name, 1) == 0:
            if add_arg is not None:
                self.shm_command(add_arg['cmd_name'], add_arg['cmd_size'], add_arg['data_type'], add_arg['data'])
            self.shm_command(cmd_name)

            if self.sync_mode:
                while self.shm_access(cmd_name, 1):
                    time.sleep(0.04)
                ret = self.shm_access(cmd_return(cmd_name), 1)
                # sem post
                return ret
            else:
                return True
        else:
            return False

    def direct_teaching(self, mode):
        if mode:
            self.command_set_no_busy_logic(INDY_SHM_CLIENT_ADDR8_CMD_SWITCH_DIRECT_TEACHING)
        else:
            self.command_set_no_busy_logic(INDY_SHM_CLIENT_ADDR8_CMD_FINISH_DIRECT_TEACHING)

    # Set global robot variables
    def set_sync_mode(self, sync):
        self.sync_mode = sync

    def set_home_pos(self, q=None):
        if q is None:
            return self.command_set_no_busy_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_HOME_POS_CURR)
        else:
            add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_HOME_POS_QVECTOR,
                       'cmd_size': self.joint_dof * 8,
                       'data_type': '%sd' % self.joint_dof,
                       'data': [deg2rad(x) for x in q]}
            return self.command_set_no_busy_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_HOME_POS, add_arg)

    def set_default_tcp(self, tcp):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_TCP_DEFAULT_XYZUVW,
                   'cmd_size': 6 * 8,
                   'data_type': '6d',
                   'data': [x if i < 3 else deg2rad(x) for x, i in zip(tcp, range(0, 6))]}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_TCP_DEFAULT, add_arg)

    def set_tcp_comp(self, tcp):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_TCP_COMP_XYZUVW,
                   'cmd_size': 6 * 8,
                   'data_type': '6d',
                   'data': [x if i < 3 else deg2rad(x) for x, i in zip(tcp, range(0, 6))]}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_TCP_COMP, add_arg)

    def rev_tcp_comp(self):
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_TCP_COMP_REVOKE)

    def set_reference_frame(self, ref):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_REF_FRAME_DIRECT_XYZUVW,
                   'cmd_size': 6 * 8,
                   'data_type': '6d',
                   'data': [x if i < 3 else deg2rad(x) for x, i in zip(ref, range(0, 6))]}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_REF_FRAME_DIRECT, add_arg)

    def set_collision_level(self, level):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR32_VAL_COLLISION_LEVEL,
                   'cmd_size': 4,
                   'data_type': 'I',
                   'data': level}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_COLIISION_LEVEL, add_arg)

    def set_joint_vel_level(self, vel):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR32_VAL_JMOVE_VEL_LEVEL,
                   'cmd_size': 4,
                   'data_type': 'I',
                   'data': vel}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_JMOVE_VEL_LEVEL, add_arg)

    def set_task_vel_level(self, vel):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR32_VAL_TMOVE_VEL_LEVEL,
                   'cmd_size': 4,
                   'data_type': 'I',
                   'data': vel}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_TMOVE_VEL_LEVEL, add_arg)

    def set_joint_waypoint_time(self, wp_time):
        if wp_time < 0.5:
            return False
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_JMOVE_TIME,
                   'cmd_size': 8,
                   'data_type': 'd',
                   'data': wp_time}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_JMOVE_WTIME, add_arg)

    def set_task_waypoint_time(self, wp_time):
        if wp_time < 0.5:
            return False
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_TMOVE_TIME,
                   'cmd_size': 8,
                   'data_type': 'd',
                   'data': wp_time}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_TMOVE_WTIME, add_arg)

    def set_task_base(self, mode):
        # 0 for reference frame
        # 1 for TCP
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR32_VAL_TCP_CTRL_MODE,
                   'cmd_size': 4,
                   'data_type': 'I',
                   'data': mode}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_TCP_CTRL_MODE, add_arg)

    def set_joint_blend_radius(self, radius):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_JOINT_BLEND_RADIUS,
                   'cmd_size': 8,
                   'data_type': 'd',
                   'data': deg2rad(radius)}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_JOINT_BLEND_RAD, add_arg)

    def set_task_blend_radius(self, radius):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_TASK_BLEND_RADIUS,
                   'cmd_size': 8,
                   'data_type': 'd',
                   'data': deg2rad(radius)}
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_SET_TASK_BLEND_RAD, add_arg)

    # Get global robot variables
    def get_default_tcp(self):
        return [x if i < 3 else rad2deg(x) for x, i in
                zip(self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_TCP_DEFAULT, 6 * 8, '6d'), range(0, 6))]

    def get_tcp_comp(self):
        return [x if i < 3 else rad2deg(x) for x, i in
                zip(self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_TCP_COMP, 6 * 8, '6d'), range(0, 6))]

    def get_reference_frame(self):
        return [x if i < 3 else rad2deg(x) for x, i in
                zip(self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_REFFRAME_TREF, 6 * 8, '6d'), range(0, 6))]

    def get_reference_frame_point(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_REFFRAME_POINTS, 9 * 8, '9d')

    def get_tool_property(self):
        shm_val = self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_TOOL_PROPERTY, 4 * 8, '4d')
        res = {'mass': shm_val[0],
               'x': shm_val[1],
               'y': shm_val[2],
               'z': shm_val[3]}
        return res

    def get_user_data(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_USER_STRUCT_DATA, 4, 'i')
        # User configuration data

    def get_collision_level(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_COLLISION_LEVEL, 4, 'I')

    def get_joint_vel_level(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_JMOVE_VEL_LEVEL, 4, 'I')

    def get_joint_acc_level(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_JMOVE_ACC_LEVEL, 4, 'I')

    def get_task_vel_level(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_TMOVE_VEL_LEVEL, 4, 'I')

    def get_task_acc_level(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_TMOVE_ACC_LEVEL, 4, 'I')

    def get_joint_waypoint_time(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_JMOVE_WAYPOINT_TIME, 8, 'd')

    def get_task_waypoint_time(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_TMOVE_WAYPOINT_TIME, 8, 'd')

    def get_joint_home(self):
        return [rad2deg(x) for x in self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_JOINT_HOME, 6 * 8, '6d')]

    def get_task_home(self):  # for impedance control
        return [x if i < 3 else rad2deg(x) for x, i in
                zip(self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_TASK_HOME, 6 * 8, '6d'), range(0, 6))]

    def get_mount_angle(self):
        # [y-rot, z-rot] deg
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_ROBOT_MOUNT_ANGLE, 16, '2d')

    def get_joint_blend_radius(self):
        return rad2deg(self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_JOINT_BLEND_RADIUS, 8, 'd'))

    def get_task_blend_radius(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CONFIG_TASK_BLEND_RADIUS, 8, 'd')

    # Get robot data
    def get_rt_data(self):
        attr = ['time', 'task_time', 'max_task_time', 'compute_time', 'max_compute_time',
                'ecat_time', 'max_ecat_time', 'ecat_master_state', 'ecat_slave_num']
        shm_val = self.shm_access(INDY_SHM_RT_ADDR_STRUCT_DATA, 64, 'd6Q2L')
        res = {}
        for att in attr:
            res[att] = shm_val[attr.index(att)]
        return res

    def get_joint_pos(self):
        shm_val = self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_Q, 8 * 6, '6d')
        res = []
        for val in shm_val:
            res.append(rad2deg(val))
        return res

    def get_joint_vel(self):
        return [rad2deg(x) for x in self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_QDOT, 8*self.joint_dof, '%sd'%self.joint_dof)]

    def get_task_pos(self):
        shm_val = self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_P, 8 * 6, '6d')
        pos = list(shm_val[3:6]) + list(shm_val[0:3])
        return [x if i < 3 else rad2deg(x) for x, i in zip(pos, range(0, 6))]

    def get_task_vel(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_PDOT, 48, '6d')

    def get_control_torque(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_TAU, 8 * self.joint_dof, '%sd' % self.joint_dof)

    def get_actual_torque(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_TAU_ACT, 8 * self.joint_dof, '%sd' % self.joint_dof)

    def get_external_torque(self):
        return self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_TAU_EXT, 8 * self.joint_dof, '%sd' % self.joint_dof)

    # def get_joint_acc(self):
    #     return [rad2deg(x) for x in self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_QDDOT, 8*self.joint_dof, '%sd'%self.joint_dof)]
    #
    # def get_task_acc(self):
    #     return self.shm_access(INDY_SHM_ROBOT_ADDR_CTRL_PDDOT, 48, '6d')

    # Robot emergency data
    def get_last_emergency_info(self):
        attr = ['error_code', 'args_int', 'args_double', 'time']
        error_code = ['EMG button', 'Collision', 'Position limit', 'Vel/Acc limit', 'Motor state error',
                      'Torque limit', 'Connection lost', 'Path error', 'Endtool error', 'Singularity',
                      'Overcurrent', 'Near position limit', 'Near velocity limit', 'Near singularity',
                      'No error']
        shm_val = self.shm_access(INDY_SHM_ROBOT_ADDR_EMERG_STRUCT_DATA, 48, '4i4d')

        res = {attr[0]: error_code[shm_val[0] - 1],
               attr[1]: shm_val[1:4],
               attr[2]: shm_val[4:7],
               attr[3]: shm_val[7]}

        return res

    # Motion command
    def execute_move(self, cmd_name):
        cmd_name += "\0"
        name_len = len(cmd_name)
        if name_len > 256:
            return False
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDRCUST_VAL_EXECUTE_COMMAND_NAME,
                   'cmd_size': name_len,
                   'data_type': '%ss' % name_len,
                   'data': cmd_name.encode()}
        print(add_arg)
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_EXECUTE_COMMAND, add_arg)

    def go_home(self):
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_JMOVE_HOME)

    def go_zero(self):
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_JMOVE_ZERO)

    def joint_move_to(self, q):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_JMOVE_TO_QVECTOR,
                   'cmd_size': self.joint_dof*8,
                   'data_type': '%sd'%self.joint_dof,
                   'data': [deg2rad(x) for x in q]}
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_JMOVE_TO, add_arg)

    def joint_move_by(self, q):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_JMOVE_BY_QVECTOR,
                   'cmd_size': self.joint_dof*8,
                   'data_type': '%sd' % self.joint_dof,
                   'data': [deg2rad(x) for x in q]}
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_JMOVE_BY, add_arg)

    def task_move_to(self, p):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_TMOVE_TO_XYZUVW,
                   'cmd_size': 6*8,
                   'data_type': '%sd'%self.joint_dof,
                   'data': [x if i < 3 else deg2rad(x) for x, i in zip(p, range(0, 6))]}
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_TMOVE_TO_XYZUVW, add_arg)

    def task_move_by(self, p):
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR64_VAL_TMOVE_BY_XYZUVW,
                   'cmd_size': 6*8,
                   'data_type': '%sd' % self.joint_dof,
                   'data': [x if i < 3 else deg2rad(x) for x, i in zip(p, range(0, 6))]}
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_TMOVE_BY_XYZUVW, add_arg)

    # Waypoint move
    def joint_waypoint_append(self, q, wp_type=0, blend_radius=0):
        # wp_type: 0 (absolute), 1 (relative joint)
        # blend_radius: 0 ~ 23 [deg]

        stop_blend = True if blend_radius == 0 else False

        if self.shm_access(INDY_SHM_CLIENT_ADDR8_CMD_APPEND_JWP, 1) == 0:
            self.shm_command(INDY_SHM_CLIENT_ADDR64_VAL_JWP_WAPOINT,
                             self.joint_dof * 8, '%sd' % self.joint_dof, [deg2rad(x) for x in q])

            self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_JWP_WAPOINT_OPT,
                             4, 'i', wp_type)
            self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_JWP_WAPOINT_OPT+4,
                             1, '?', stop_blend)
            self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_JWP_WAPOINT_OPT+5,
                             8, 'd', deg2rad(blend_radius))
            self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_APPEND_JWP)

            while self.shm_access(INDY_SHM_CLIENT_ADDR8_CMD_APPEND_JWP, 1):
                time.sleep(0.001)

            if self.shm_access(cmd_return(INDY_SHM_CLIENT_ADDR8_CMD_APPEND_JWP), 1):
                return True
            else:
                return False
        else:
            return False


    def joint_waypoint_remove(self):
        return self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_REMOVE_JWP)

    def joint_waypoint_clean(self):
        return self.command_set_logic(INDY_SHM_CLIENT_ADDR8_CMD_CLEAN_JWP)
        # return self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_CLEAN_JWP)

    def joint_waypoint_execute(self):
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_EXECUTE_JWP_MOVE)

    def task_waypoint_append(self, p, wp_type=0, blend_radius=0):
    	# p : xyzuvw [m, degree]
        # wp_type: 0 (absolute), 2 (relative task)
        # blend radius: 0.02 ~ 0.2 [m]

        stop_blend = True if blend_radius == 0 else False

        if self.shm_access(INDY_SHM_CLIENT_ADDR8_CMD_APPEND_TWP, 1) == 0:
            self.shm_command(INDY_SHM_CLIENT_ADDR64_VAL_TWP_WAPOINT,
                             6 * 8, '%sd' % 6, [x if i < 3 else deg2rad(x) for x, i in zip(p, range(0, 6))])
            self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_TWP_WAPOINT_OPT,
                             4, 'i', wp_type)
            self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_TWP_WAPOINT_OPT + 4,
                             1, '?', stop_blend)
            self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_TWP_WAPOINT_OPT + 5,
                             8, 'd', blend_radius)
            self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_APPEND_TWP)

            while self.shm_access(INDY_SHM_CLIENT_ADDR8_CMD_APPEND_TWP, 1):
                time.sleep(0.001)

            if self.shm_access(cmd_return(INDY_SHM_CLIENT_ADDR8_CMD_APPEND_TWP), 1):
                return True
            else:
                return False
        else:
            return False


    def task_waypoint_remove(self):
        return self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_REMOVE_TWP)

    def task_waypoint_clean(self):
        return self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_CLEAN_TWP)

    def task_waypoint_execute(self):
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_EXECUTE_TWP_MOVE)

    # Conty's move command
    def execute_move(self, cmd_name):
        cmd_name += "\0"
        name_len = len(cmd_name)
        if name_len > 256:
            return False
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDRCUST_VAL_EXECUTE_COMMAND_NAME,
                   'cmd_size': name_len,
                   'data_type': '%ss' % name_len,
                   'data': cmd_name.encode()}
        print(add_arg)
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_EXECUTE_COMMAND, add_arg)

    def joint_move_waypoint(self, name):
        name += "\0"
        name_len = len(name)
        if name_len > 64:
            return False
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDRCUST_VAL_JMOVE_WAYPOINT_NAME,
                   'cmd_size': name_len,
                   'data_type': '%ss' % name_len,
                   'data': name.encode()}
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_JMOVE_WAYPOINT_NAME, add_arg)

    def task_move_waypoint(self, name):
        name += "\0"
        name_len = len(name)
        if name_len > 64:
            return False
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDRCUST_VAL_TMOVE_WAYPOINT_NAME,
                   'cmd_size': name_len,
                   'data_type': '%ss' % name_len,
                   'data': name.encode()}
        return self.command_motion_logic(INDY_SHM_CLIENT_ADDR8_CMD_TMOVE_WAYPOINT_NAME, add_arg)

    # Program control
    def start_current_program(self):
        self.command_program_logic(INDY_SHM_CLIENT_ADDR8_CMD_START_CURR_PROGRAM)

    def pause_current_program(self):
        # 200ms
        self.command_program_pause_logic(INDY_SHM_CLIENT_ADDR8_CMD_PAUSE_CURR_PROGRAM)
        # self.command_program_compact_logic(INDY_SHM_CLIENT_ADDR8_CMD_PAUSE_CURR_PROGRAM)

    def resume_current_program(self):
        self.command_program_compact_logic(INDY_SHM_CLIENT_ADDR8_CMD_RESUME_CURR_PROGRAM)

    def stop_current_program(self):
        self.command_program_compact_logic(INDY_SHM_CLIENT_ADDR8_CMD_STOP_CURR_PROGRAM)

    def start_registered_default_program(self):
        self.command_program_logic(INDY_SHM_CLIENT_ADDR8_CMD_START_DEFAULT_PROGRAM)

    def start_default_program(self):
        self.start_registered_default_program()

    def register_default_program(self, idx):
        if idx < -1 or idx > 9:
            return False
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR32_VAL_REG_DEFAULT_PRGRAM_IDX,
                   'cmd_size': 4,
                   'data_type': 'I',
                   'data': idx}
        self.command_program_compact_logic(INDY_SHM_CLIENT_ADDR8_CMD_REG_DEFAULT_PROGRAM, add_arg)

    # Digital/Analog IO
    # def shm_command(self, shm_name, data_size=1, data_type='', shm_data=None):
    def set_el4104_ao(self, arr):
        if isinstance(arr, list) and len(arr) == 4:
            self.shm_command(INDY_SHM_EL4104_AO, 2*4, '4H', arr)
        else:
            print("변수 4개 리스트를 입력하세요")

    def get_el1008_di(self):
        res_data = self.shm_access(INDY_SHM_EL1008_DI, 1, 'B')

        result = [0, 0, 0, 0, 0, 0, 0, 0]
        if res_data < 256:
            b = list("{0:b}".format(res_data))
            for i in range(len(b)):
                result[i] = int(b[len(b)-i-1])
            return result
        else:
            print("out of range :", res_data)
            return None

    def set_el2008_do(self, arr):
        if len(arr) != 8:
            print('Input should be 8 bits array')
            return None

        bits = [1 if i > 0 else 0 for i in arr]

        s = 0
        iter_count = 0
        for b in bits:
            s = s + b*pow(2, iter_count)
            iter_count = iter_count + 1

        self.shm_command(INDY_SHM_EL2008_DO, 1, 'B', s)
        return None

    def set_el2008_do_val(self, addr, val):
        current = self.get_el1008_di()
        current[addr] = val
        return self.set_el2008_do(current)


    def get_di(self):
        return self.shm_access(INDY_SHM_SERVER_ADDRCUST_SMART_DI, 1 * 32, '32B')

    def set_do(self, *args):
        if len(args) == 1:
            arr = args[0]
            if type(arr) != list:
                print("Error: 32-size list should be given.")
                return False
            self.shm_command(INDY_SHM_SERVER_ADDRCUST_SMART_DO, 32, '32B', arr)
        elif len(args) == 2:
            idx = args[0]
            val = args[1]
            self.shm_command(INDY_SHM_SERVER_ADDRCUST_SMART_DO + idx, 1, 'B', val)
        else:
            print("Invalid argument")
            print("set_do(arr) or set_do(idx, val)")

    def get_do(self):
        return self.shm_access(INDY_SHM_SERVER_ADDRCUST_SMART_DO, 1 * 32, '32B')

    def get_ai(self):
        return self.shm_access(INDY_SHM_SERVER_ADDRCUST_SMART_AI, 2 * 2, 'HH')

    def set_ao(self, *args):
        if len(args) == 1:
            arr = args[0]
            if type(arr) != list:
                print("Error: 2-size list should be given.")
                return False
            self.shm_command(INDY_SHM_SERVER_ADDRCUST_SMART_AO, 4, '2H', arr)
        elif len(args) == 2:
            idx = args[0]
            val = args[1]
            self.shm_command(INDY_SHM_SERVER_ADDRCUST_SMART_AO + idx, 1, 'I', val)
        else:
            print("Invalid argument")
            print("set_ao(arr) or set_ao(idx, val)")

    def get_ao(self):
        return self.shm_access(INDY_SHM_SERVER_ADDRCUST_SMART_AO, 2 * 2, 'HH')

    def set_endtool_do(self, idx, val):
        # endtool_type:
        # 0: NPN, 1: PNP, 2: Not use, 3: eModi
        arr = [0, 0, 0, 0]
        arr[idx] = val
        self.shm_command(INDY_SHM_SERVER_ADDRCUST_ENDTOOL_DO, 4, '4B', arr)

    def get_endtool_do(self):
        return self.shm_access(INDY_SHM_SERVER_ADDRCUST_ENDTOOL_DO, 4, '4B')

    # F/T sensor data (verification is required)
    def get_robot_ft_raw(self):
        return self.shm_access(INDY_SHM_SERVER_ADDRCUST_EXTRA_IO_FTSENSOR_ROBOT_CAN_RAW, 48, '6d')

    def get_robot_ft(self):
        return self.shm_access(INDY_SHM_SERVER_ADDRCUST_EXTRA_IO_FTSENSOR_ROBOT_CAN, 48, '6d')

    def get_cb_ft_raw(self):
        return self.shm_access(INDY_SHM_SERVER_ADDRCUST_EXTRA_IO_FTSENSOR_CB_CAN_RAW, 48, '6d')

    def get_cb_ft(self):
        return self.shm_access(INDY_SHM_SERVER_ADDRCUST_EXTRA_IO_FTSENSOR_CB_CAN, 48, '6d')

    # Direct variables
    def read_direct_variable(self, dv_type, dv_addr, dv_len=None):
        if dv_len is None:
            if dv_type == 0 or dv_type == 'B':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_BYTE, 1000, '1000B')[dv_addr]
            elif dv_type == 1 or dv_type == 'W':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_WORD, 2*1000, '1000h')[dv_addr]
            elif dv_type == 2 or dv_type == 'I':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_DWORD, 4*1000, '1000i')[dv_addr]
            elif dv_type == 3 or dv_type == 'L':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_LWORD, 8*1000, '1000q')[dv_addr]
            elif dv_type == 4 or dv_type == 'F':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_FLOAT, 6, 4*1000, '1000f')[dv_addr]
            elif dv_type == 5 or dv_type == 'D':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_DFLOAT, 8*1000, '1000d')[dv_addr]
            elif dv_type == 10 or dv_type == 'M':
                self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_MODBUS_ADDR, 4, 'I', dv_addr)
                self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_READ_MODBUS_VAR, 1)

                while self.shm_access(INDY_SHM_CLIENT_ADDR8_CMD_READ_MODBUS_VAR, 1):
                    pass
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_MODBUS_USER, 2*1000, '1000H')[0]
            else:
                print("Invalid direct variable type")
        else:
            if dv_type == 0 or dv_type == 'B':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_BYTE, 1000, '1000B')[dv_addr:dv_addr+dv_len]
            elif dv_type == 1 or dv_type == 'W':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_WORD, 2*1000, '1000h')[dv_addr:dv_addr+dv_len]
            elif dv_type == 2 or dv_type == 'I':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_DWORD, 4*1000, '1000i')[dv_addr:dv_addr+dv_len]
            elif dv_type == 3 or dv_type == 'L':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_LWORD, 8*1000, '1000q')[dv_addr:dv_addr+dv_len]
            elif dv_type == 4 or dv_type == 'F':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_FLOAT, 4*1000, '1000f')[dv_addr:dv_addr+dv_len]
            elif dv_type == 5 or dv_type == 'D':
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_DFLOAT, 8*1000, '1000d')[dv_addr:dv_addr+dv_len]
            elif dv_type == 10 or dv_type == 'M':
                self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_MODBUS_ADDR, 4, 'I', dv_addr)
                self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_MODBUS_LEN, 4, 'I', dv_len)
                self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_READ_MODBUS_VARS, 1)

                while self.shm_access(INDY_SHM_CLIENT_ADDR8_CMD_READ_MODBUS_VARS, 1):
                    pass
                return self.shm_access(INDY_SHM_DIRECT_VAR_ADDR_MODBUS_USER, 2*1000, '1000H')[:dv_len]
            else:
                print("Invalid direct variable type")

    def write_direct_variable(self, dv_type, dv_addr, val):
        if dv_type == 0 or dv_type == 'B':
            self.shm_command(INDY_SHM_DIRECT_VAR_ADDR_BYTE + dv_addr, 1, 'B', val)
        elif dv_type == 1 or dv_type == 'W':
            self.shm_command(INDY_SHM_DIRECT_VAR_ADDR_WORD + dv_addr*2, 2, 'h', val)
        elif dv_type == 2 or dv_type == 'I':
            self.shm_command(INDY_SHM_DIRECT_VAR_ADDR_DWORD+dv_addr*4, 4, 'i', val)
        elif dv_type == 3 or dv_type == 'L':
            self.shm_command(INDY_SHM_DIRECT_VAR_ADDR_LWORD+dv_addr*8, 8, 'q', val)
        elif dv_type == 4 or dv_type == 'F':
            self.shm_command(INDY_SHM_DIRECT_VAR_ADDR_FLOAT+dv_addr*4, 4, 'f', val)
        elif dv_type == 5 or dv_type == 'D':
            self.shm_command(INDY_SHM_DIRECT_VAR_ADDR_DFLOAT+dv_addr*8, 8, 'd', val)
        elif dv_type == 10 or dv_type == 'M':
            self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_MODBUS_ADDR, 4, 'I', dv_addr)
            self.shm_command(INDY_SHM_CLIENT_ADDR32_VAL_MODBUS_DATA, 2, 'H', val)

            self.shm_command(INDY_SHM_CLIENT_ADDR8_CMD_WRITE_MODBUS_VAR, 1)
            while self.shm_access(INDY_SHM_CLIENT_ADDR8_CMD_WRITE_MODBUS_VAR, 1):
                pass
        else:
            print("Invalid direct variable type")

    # External trajectory (not yet implemented in the framework)
    def ext_command_logic(self, cmd_name, add_arg=None):
        robot_state = self.get_robot_status()
        is_emg = robot_state['emergency']
        is_busy = robot_state['busy']

        if self.sync_mode:
            while is_emg:
                time.sleep(0.005)
        elif is_emg:
            return False

        if is_busy:
            return False
        elif self.shm_access(cmd_name, 1) == 0:

            if self.sync_mode:
                # wait semaphore
                pass
            print(add_arg)
            null_char = "\0".encode()
            self.shm_command(add_arg['cmd_name'], add_arg['cmd_size'], add_arg['data_type'], add_arg['data'])
            self.shm_command(add_arg['cmd_name']+add_arg['cmd_size'], add_arg['cmd_size'], '', null_char)
            self.shm_command(cmd_name)

            if self.sync_mode:
                while self.shm_access(cmd_name, 1):
                    time.sleep(0.04)
                time.sleep(0.04)
                if self.shm_access(cmd_return(cmd_name), 1):
                    while self.get_robot_status()['busy']:
                        time.sleep(0.005)

                    # post semaphore
                    return self.get_robot_status()['movedone']
                else:
                    # post semaphore
                    return False
            else:
                return True
        else:
            return False

    # External interpolator
    def ext_move_bin_file(self, file_name):
        req_ext_data = file_name.encode('ascii')
        req_ext_data_size = len(file_name)

        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDRCUST_VAL_EXTMOVE_BIN_FILE_PATH,
                   'cmd_size': req_ext_data_size,
                   'data_type': '%ss' % req_ext_data_size,
                   'data': req_ext_data}
        return self.ext_command_logic(INDY_SHM_CLIENT_ADDR8_CMD_EXTMOVE_BIN_FILE, add_arg)

    def ext_move_txt_file(self, file_name):
        req_ext_data = file_name.encode('ascii')
        req_ext_data_size = len(file_name)

        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDRCUST_VAL_EXTMOVE_TXT_FILE_PATH,
                   'cmd_size': req_ext_data_size,
                   'data_type': '%ss'%req_ext_data_size,
                   'data': req_ext_data}
        return self.ext_command_logic(INDY_SHM_CLIENT_ADDR8_CMD_EXTMOVE_TXT_FILE, add_arg)

    # Fric ID
    def set_fric_id(self, mode):
        # mode 1 : start
        # mode 3 : stop
        self.shm_command(INDY_SHM_ROBOT_ADDR_FRIC_ID_LOGGING_TRIGGER, 4, 'I', mode)

    # Jog
    def joint_jog_move(self, vel, q1, q2, q3, q4, q5, q6):
        # arg: [vel_level, direction, task_base]
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR32_VAL_JOGMOVE_JOINT,
                   'cmd_size': 4*7,
                   'data_type': '7i',
                   'data': [vel, q1, q2, q3, q4, q5, q6]}
        return self.command_jogging_logic(INDY_SHM_CLIENT_ADDR8_CMD_JOGMOVE_JOINT, add_arg)

    def task_jog_move(self, vel, x, y, z, u, v, w, task_base):
        # arg: [vel_level, direction, tbase : 0(base), 1(tcp)]
        add_arg = {'cmd_name': INDY_SHM_CLIENT_ADDR32_VAL_JOGMOVE_TASK,
                   'cmd_size': 4*8,
                   'data_type': '8i',
                   'data': [vel, x, y, z, u, v, w, task_base]}
        return self.command_jogging_logic(INDY_SHM_CLIENT_ADDR8_CMD_JOGMOVE_TASK, add_arg)

    def stop_jog(self):
        # ~ 200ms
        return self.command_stop_logic(INDY_SHM_CLIENT_ADDR8_CMD_STOP_JOGMOVE)


