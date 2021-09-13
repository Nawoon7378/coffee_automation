from indy_utils.indy_shm import *

from time import sleep
import time
import signal, sys, os
import numpy as np

indy_master = IndyShmCommand()
indy_master.set_sync_mode(False)
COMMANDER_ADDR = 600

def reset_cmd():
    sleep(0.05)
    indy_master.write_direct_variable(0, COMMANDER_ADDR, 0)

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    indy_master.stop_jog()
    sys.exit(-1)

def main():
    indy_master.write_direct_variable(0, COMMANDER_ADDR, 0)
    indy_master.set_task_vel_level(5)

    while True:
        cmd = indy_master.read_direct_variable(0, COMMANDER_ADDR)

        if cmd == 1:
            while indy_master.get_robot_status()['busy']:
                sleep(0.05)
            
            indy_master.set_reference_frame([0,0,0,7,0,0])
            
            target_pos = indy_master.get_task_pos()
            target_pos[1] = -0.90
            detected=False

            indy_master.task_move_to(target_pos)

            while True:
                if indy_master.get_di()[5]:
                    detected_pos = indy_master.get_task_pos()
                    indy_master.stop_motion()
                    detected = True
                    break
                
                if not indy_master.get_robot_status()['busy']:
                    break
                
                sleep(0.05)

            if detected:
                indy_master.task_move_to(detected_pos)
                while not indy_master.get_robot_status()['busy']:
                    sleep(0.05)
                while indy_master.get_robot_status()['busy']:
                    sleep(0.05)

                indy_master.write_direct_variable(0, 200, 1)
            else:
                indy_master.write_direct_variable(0, 200, 2)

            indy_master.set_reference_frame([0,0,0,0,0,0])
            reset_cmd()
        
        sleep(0.05)
    
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    os.system("taskset -p -c 0,1 %d" % os.getpid())

    main()

