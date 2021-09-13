# di -> modbus M (M000 ~ M032)
# modbus M -> do ((M100 ~ M132))

import sys
from posix_ipc import SharedMemory
from os import read, write, lseek, SEEK_SET
from struct import pack, unpack
import math
import time
from threading import Lock
import signal, os
import random

INDY_SHM_ROBOT_ADDR_ERROR_STRUCT_DATA = 0x061000

INDY_SUPPORT_INDYGO_SHM_NAME = 'indyGoShm'
INDY_SUPPORT_INDYGO_SHM_LEN = 4096
INDY_SHM_MGR_OFFSET = 64

## Size Information of Shared Memory
INDY_SHM_NAME = "indySHM"
INDY_SHM_LEN = 0x1000000  # 16MB		== 0x000000~0xFFFFFF (~16777216)

INDY_SHM_SERVER_ADDRCUST_SMART_DI = 0x380000  # 00~1F (32*1)
INDY_SHM_SERVER_ADDRCUST_SMART_DO = 0x380020  # 20~3F (32*1)

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

from pyModbusTCP.client import ModbusClient
c = ModbusClient(host="127.0.0.1", auto_open=True, auto_close=True)

def main():
    indy_master = IndyShmCommand()

    while True:
        time.sleep(0.001)
        regs = c.read_holding_registers(100, 32)
        indy_master.set_do(regs)

        dis = indy_master.get_di()
        c.write_multiple_registers(0, dis)
        
def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    sys.exit(-1)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    os.system("taskset -p -c 0,1 %d" % os.getpid())

    main()