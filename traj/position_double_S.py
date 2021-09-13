import numpy as np
import matplotlib.pylab as plt

"""
######################### Input ######################### 
p0:List - start pose (m)
p1:List - end pose (m)
max_vel:Float - maximum velocity (m/s) 
a0:Float - acceleration (m/s^2)
a1:Float - deceleration (m/s^2)
time_rate:Float - time step (millisecond)

######################### Output ######################### 
res_p:List - pose trajectory
res_v:List - velocity trajectory
res_a:List - acceleration trajectory 
"""

def asymmetric_double_S_task_move(p0, p1, max_vel, a0, a1, time_rate=0.25):   
    pos0 = p0[0:3]
    rot0 = p0[3:6]
    
    pos1 = p1[0:3]
    rot1 = p1[3:6]
    
    assert np.array_equal(rot0, rot1), f'Currently rotation is not supported'
    assert a0 != 0 or a1 != 0, f'Zero acceleration is infeasible'

    dist_pos = np.linalg.norm(np.array(pos1) - np.array(pos0))
    dist_critical = max_vel*max_vel/2*(a0+a1)/a0/a1
    #print(dist_pos, dist_critical)

    assert dist_pos != 0, f'p0 and p1 should be different'
    dir_vec = (np.array(pos1) - np.array(pos0))/dist_pos
    
    pos_arr = []
    vel_arr = []
    acc_arr = []
    t = 0
    dt = time_rate*0.001
    
    pos_cur = np.array(pos0)
    vel_cur = np.array([0, 0, 0])
    acc_cur = np.array([0, 0, 0])
    
    pos_arr.append(pos_cur)
    vel_arr.append(vel_cur)
    acc_arr.append(acc_cur)
    
    if dist_pos < dist_critical:
        v_max = np.sqrt(2*dist_pos*a0*a1/(a0+a1))
        t0 = v_max/a0
        t1 = v_max/a1
        while t < t0 + t1:
            if t < t0:
                acc_cur = a0*dir_vec
            else:
                acc_cur = -a1*dir_vec

            pos_cur = pos_cur + vel_cur*dt
            vel_cur = vel_cur + acc_cur*dt
            
            pos_arr.append(pos_cur)
            vel_arr.append(vel_cur)
            acc_arr.append(acc_cur)
            t = t + dt
            
    else:
        v_max = max_vel
        dist_const_vel = dist_pos - dist_critical
        t0 = v_max/a0
        t1 = dist_const_vel/v_max
        t2 = v_max/a1
        
        while t < t0 + t1 + t2:
            if t < t0:
                acc_cur = a0*dir_vec
            elif t < t0 + t1:
                acc_cur = np.array([0, 0, 0])
            else:
                acc_cur = -a1*dir_vec
                
            pos_cur = pos_cur + vel_cur*dt
            vel_cur = vel_cur + acc_cur*dt
    
            pos_arr.append(pos_cur)
            vel_arr.append(vel_cur)
            acc_arr.append(acc_cur)
            t = t + dt

    assert np.linalg.norm(vel_cur) <= a1, f'Final velocity is too high. Abrupt stop occurs'
    assert np.linalg.norm(pos_cur-np.array(pos1)) <= 0.0005, f'Final position error is larger than 50 um (pos_cur:{pos_cur[0]}, {pos_cur[1]}, {pos_cur[2]})'
    
    res_p = []
    res_v = []
    res_a = []
    for i in range(len(pos_arr)):
        res_p.append(np.concatenate((pos_arr[i], np.array(rot0)), axis=None).tolist())
        res_v.append(np.concatenate((vel_arr[i], np.array([0, 0, 0])), axis=None).tolist())
        res_a.append(np.concatenate((acc_arr[i], np.array([0, 0, 0])), axis=None).tolist())
        
    return res_p, res_v, res_a


def test(p, v, a):
    """
    Function test
    """

    time = []
    dist = []
    velocity = []
    acceleration = []

    t = 0
    for i in range(len(p)):
        dist.append(np.linalg.norm(np.array(p[i])-np.array(p0)))
        velocity.append(np.linalg.norm(np.array(v[i])))
        acceleration.append(np.linalg.norm(np.array(a[i])))
        time.append(t)
        t = t + 0.001*0.25
        

    ax1 = plt.subplot(3,1,1)
    ax1.plot(time, dist)
    plt.xlabel('time (s)')
    plt.ylabel('dist. (m)')
    ax2 = plt.subplot(3,1,2)
    ax2.plot(time, velocity)
    plt.xlabel('time (s)')
    plt.ylabel('vel. (m/s)')
    ax3 = plt.subplot(3,1,3)
    ax3.plot(time, acceleration)
    plt.xlabel('time (s)')
    plt.ylabel('acc. (m/s^2)')

    plt.tight_layout()
    plt.show()


def get_traj_file(p, v, a):
    from datetime import datetime
    # with open("{}_sstraj.txt".format(datetime.now().strftime("%H%M%S")), "w") as f:
    with open("noodle_shake.txt", "w") as f:
        f.write("2 4000 3 6 {} \n".format(len(p)))
        for i in range(len(p)):
            for j in range(6):
                f.write("{} ".format(p[i][j]))
            for j in range(6):
                f.write("{} ".format(v[i][j]))
            for j in range(6):
                f.write("{} ".format(a[i][j]))
            f.write("\n")

import math
# 여기 잡기

p0 = [0.29821036402859297, -0.6030438179393439, 0.6633512408096686, -88.26113741825895, -129.50595761918606, 172.0283260911396]
p1 = [0.2975845449158217, -0.602885826835213, 0.5644754330392855, -88.26113741825895, -129.50595761918606, 172.0283260911396]

def deg2rad(p):
    return [p[i] if i < 3 else math.radians(p[i]) for i in range(6)]
p, v, a = asymmetric_double_S_task_move(deg2rad(p0), deg2rad(p1), max_vel=0.2, a0=1, a1=10, time_rate=0.25)

test(p, v, a)
get_traj_file(p, v, a)
