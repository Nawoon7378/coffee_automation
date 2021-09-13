from indy_utils.indy_shm import *

from time import sleep
import time
import signal, sys, os
import numpy as np

indy_master = IndyShmCommand()
tic = {}
COMMANDER_ADDR = 600

def wait_for_motion_finish():
    while indy_master.get_robot_status()['busy']:
        pass

def reset_cmd():
    sleep(0.05)
    indy_master.write_direct_variable(0, COMMANDER_ADDR, 0)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    indy_master.stop_jog()
    sys.exit(-1)

def main():

    prev_task_pos_left = indy_master.get_task_pos()
    prev_task_pos_right = indy_master.get_task_pos()

    indy_master.write_direct_variable(0, COMMANDER_ADDR, 0)

    while True:
        cmd = indy_master.read_direct_variable(0, COMMANDER_ADDR)
        isRight = indy_master.get_di()[9]

        if cmd == 1:
            wait_for_motion_finish()
            indy_master.set_reference_frame([0,0,0,7,0,0])

            if isRight:
                if indy_master.read_direct_variable(0, 151) == 1:
                    target = [p for p in prev_task_pos_right]
                    target[1] = target[1] + 0.02
                    indy_master.set_task_vel_level(5)
                    indy_master.task_move_to(target)
            else:
                if indy_master.read_direct_variable(0, 150) == 1:
                    target = [p for p in prev_task_pos_left]
                    target[1] = target[1] + 0.02
                    indy_master.set_task_vel_level(5)
                    indy_master.task_move_to(target)

            wait_for_motion_finish()

            while True:
                indy_master.task_jog_move(2,0,-1,0,0,0,0,0) # v, xyzuvw, base

                if indy_master.get_task_pos()[1] < -0.90:
                    indy_master.write_direct_variable(0, 200, 2)
                    break

                if indy_master.get_di()[5]:
                    if isRight:
                        prev_task_pos_right = indy_master.get_task_pos()
                    else:
                        prev_task_pos_left = indy_master.get_task_pos()

                    indy_master.write_direct_variable(0, 200, 1)
                    break

            indy_master.stop_jog()
            indy_master.set_reference_frame([0,0,0,0,0,0])
            reset_cmd()

        sleep(0.05)
    
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    os.system("taskset -p -c 0,1 %d" % os.getpid())

    main()

