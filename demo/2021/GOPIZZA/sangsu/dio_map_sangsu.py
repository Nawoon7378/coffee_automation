from time import sleep

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

def init_do(indy_master):
    indy_master.set_do(DO_DICT['pusher_power'], 0)
    indy_master.set_do(DO_DICT['destacker_up'], 0)
    indy_master.set_do(DO_DICT['destacker_down'], 0)
    indy_master.set_do(DO_DICT['cutting_station_up'], 0)
    indy_master.set_do(DO_DICT['cutting_station_down'], 0)
    indy_master.set_do(DO_DICT['drizzle_power'], 0)
    indy_master.set_do(DO_DICT['alarm'], 0)
    indy_master.set_do(DO_DICT['mini_conv'], 1)
    indy_master.set_do(DO_DICT['main_conv'], 1)

    indy_master.set_el2008_do([0,0,0,0,0,0,0,0])

def end_do(indy_master):
    indy_master.set_do(DO_DICT['pusher_power'], 0)
    indy_master.set_do(DO_DICT['destacker_up'], 0)
    indy_master.set_do(DO_DICT['destacker_down'], 0)
    indy_master.set_do(DO_DICT['cutting_station_up'], 0)
    indy_master.set_do(DO_DICT['cutting_station_down'], 0)
    indy_master.set_do(DO_DICT['drizzle_power'], 0)
    indy_master.set_do(DO_DICT['alarm'], 0)
    indy_master.set_do(DO_DICT['mini_conv'], 0)
    indy_master.set_do(DO_DICT['main_conv'], 0)

    indy_master.set_el2008_do([0,0,0,0,0,0,0,0])

def mini_conv_stop(indy_master):
    indy_master.set_do(DO_DICT['mini_conv'], 0)

def mini_conv_move(indy_master):
    indy_master.set_do(DO_DICT['mini_conv'], 1)

def main_conv_stop(indy_master):
    indy_master.set_do(DO_DICT['main_conv'], 0)

def main_conv_move(indy_master):
    indy_master.set_do(DO_DICT['main_conv'], 1)

def pusher_push(indy_master):
    indy_master.set_do(DO_DICT['pusher_way'], 1)
    indy_master.set_do(DO_DICT['pusher_power'], 1)

def pusher_stop(indy_master):
    indy_master.set_do(DO_DICT['pusher_power'], 0)

def pusher_back(indy_master):
    indy_master.set_do(DO_DICT['pusher_way'], 0)
    indy_master.set_do(DO_DICT['pusher_power'], 1)

def destacker_up(indy_master):
    indy_master.set_do(DO_DICT['destacker_up'], 1)
    indy_master.set_do(DO_DICT['destacker_down'], 0)

def destacker_stop(indy_master):
    indy_master.set_do(DO_DICT['destacker_down'], 0)
    indy_master.set_do(DO_DICT['destacker_up'], 0)

def destacker_down(indy_master):
    indy_master.set_do(DO_DICT['destacker_up'], 0)
    indy_master.set_do(DO_DICT['destacker_down'], 1)

def cutting_station_up(indy_master):
    indy_master.set_do(DO_DICT['cutting_station_up'], 1)
    indy_master.set_do(DO_DICT['cutting_station_down'], 0)

def cutting_station_stop(indy_master):
    indy_master.set_do(DO_DICT['cutting_station_down'], 0)
    indy_master.set_do(DO_DICT['cutting_station_up'], 0)

def cutting_station_down(indy_master):
    indy_master.set_do(DO_DICT['cutting_station_down'], 1)
    indy_master.set_do(DO_DICT['cutting_station_up'], 0)

def alarm_on(indy_master):
    indy_master.set_do(DO_DICT['alarm'], 1)

def alarm_off(indy_master):
    indy_master.set_do(DO_DICT['alarm'], 0)

def gate_0_open(indy_master, EL2008_DO_LIST):
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_0_way']] = 1
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_0_power']] = 1
    indy_master.set_el2008_do(EL2008_DO_LIST)

def gate_0_stop(indy_master, EL2008_DO_LIST):
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_0_power']] = 0
    indy_master.set_el2008_do(EL2008_DO_LIST)

def gate_0_close(indy_master, EL2008_DO_LIST):
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_0_way']] = 1
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_0_power']] = 1
    indy_master.set_el2008_do(EL2008_DO_LIST)

def gate_1_open(indy_master, EL2008_DO_LIST):
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_1_way']] = 1
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_1_power']] = 1
    indy_master.set_el2008_do(EL2008_DO_LIST)

def gate_1_stop(indy_master, EL2008_DO_LIST):
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_1_power']] = 0
    indy_master.set_el2008_do(EL2008_DO_LIST)

def gate_1_close(indy_master, EL2008_DO_LIST):
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_1_way']] = 0
    EL2008_DO_LIST[EL2008_DO_DICT['stopper_1_power']] = 1
    indy_master.set_el2008_do(EL2008_DO_LIST)

#edit
# def drizzle_mayo_on(indy_master):
#     indy_master.set_do(DO_DICT['drizzle_power'],1)
#     indy_master.set_do(DO_DICT['mayo'],1)
# def drizzle_mayo_off(indy_master):
#     indy_master.set_do(DO_DICT['drizzle_power'],0)
#     indy_master.set_do(DO_DICT['mayo',0])

# def drizzle_on(indy_master,sauce_type):
#     indy_master.set_do(DO_DICT['drizzle_power'],1)
#     indy_master.set_do(DO_DICT[sauce_type],1)
# def drizzle_off(indy_master,sauce_type):
#     indy_master.set_do(DO_DICT['drizzle_power'],0)
#     indy_master.set_do(DO_DICT[sauce_type],0)

# get information
def is_gate_0_pizza_ready(DIS):
    if DIS[DI_DICT['gate_0_pizza']] == 1:
        return True
    else: 
        return False

def is_gate_1_pizza_ready(DIS):
    if DIS[DI_DICT['gate_1_pizza']] == 1:
        return True
    else: 
        return False

def is_destacker_plate_ready(DIS):
    if DIS[DI_DICT['destacker_plate']] == 1:
        return True
    else: 
        return False

def is_destacker_pizza_ready(DIS):
    if DIS[DI_DICT['destacker_pizza']] == 1:
        return True
    else: 
        return False

def is_pusher_start(DIS):
    if DIS[DI_DICT['pusher_start']] == 1:
        return True
    else: 
        return False

def is_pusher_end(DIS):
    if DIS[DI_DICT['pusher_end']] == 1:
        return True
    else: 
        return False

def is_destacker_bottom(DIS):
    if DIS[DI_DICT['destacker_bottom']] == 1:
        return True
    else: 
        return False

def is_destacker_top(DIS):
    if DIS[DI_DICT['destacker_top']] == 1:
        return True
    else: 
        return False

def is_cutting_station_bottom(DIS):
    if DIS[DI_DICT['cutting_station_bottom']] == 1:
        return True
    else: 
        return False

def is_cutting_station_middle(DIS):
    if DIS[DI_DICT['cutting_station_middle']] == 1:
        return True
    else: 
        return False

def is_cutting_station_top(DIS):
    if DIS[DI_DICT['cutting_station_top']] == 1:
        return True
    else: 
        return False

def is_pick_ready(DIS):
    if DIS[DI_DICT['pickup_plate']] == 0: #
        return True
    else: 
        return False

def is_botton_0_toggle(DIS):
    if DIS[DI_DICT['botton_0_toggle']] == 1:
        return True
    else: 
        return False


def is_botton_1(DIS):
    if DIS[DI_DICT['botton_1']] == 1:
        return True
    else: 
        return False

def is_botton_2_toggle(DIS):
    if DIS[DI_DICT['botton_2_toggle']] == 1:
        return True
    else: 
        return False

def is_botton_3_toggle(DIS):
    if DIS[DI_DICT['botton_3_toggle']] == 1:
        return True
    else: 
        return False