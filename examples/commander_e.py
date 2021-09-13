from indy_utils import indydcp_client as client
from time import sleep
import time
import signal, sys, os
import numpy as np

robot_ip = "127.0.0.1"  # Robot (Indy) IP
robot_name = "NRMK-Indy7"  # Robot name (Indy7)
indy = client.IndyDCPClient(robot_ip, robot_name)

COMMANDER_ADDR = 600
indy.connect()

def set_gripper_mode(indy, mode):
    indy.set_endtool_do(0, mode)

def set_gripper_cmd(indy, cmd):
    indy.set_endtool_do(1, cmd)

def reset_cmd():
    sleep(0.05)
    indy.write_direct_variable(0, COMMANDER_ADDR, 0)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    indy.disconnect()
    sys.exit(-1)

def main():
    indy.write_direct_variable(0, COMMANDER_ADDR, 0)

    while True:
        cmd = indy.read_direct_variable(0, COMMANDER_ADDR)

        if cmd == 1:
            while indy.get_robot_status()['busy']:
                sleep(0.05)

            set_gripper_mode(indy, 32)
            sleep(3)
            set_gripper_cmd(indy, 0)
            sleep(3)
            set_gripper_mode(indy, 16)
            sleep(3)
            set_gripper_cmd(indy, 0)
            sleep(3)
            set_gripper_mode(indy, 32)
            sleep(3)
            set_gripper_cmd(indy, 1)
            sleep(3)
            set_gripper_mode(indy, 64)
            sleep(3)
            
            reset_cmd()
        sleep(0.05)
    
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    os.system("taskset -p -c 0,1 %d" % os.getpid())

    main()

