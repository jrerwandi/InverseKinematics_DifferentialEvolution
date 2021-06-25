import math
import numpy as np
import PyKDL as kdl
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d
from time import time, sleep
from numba import njit, jit


start = time()
#cm 
link1 = 17.282
link2 = 4.9194
link3 = 20.7937
link4 = 36.4028
angle = []
yaw = 20
yaw = np.radians(yaw)
target = [-50.606269 ,  14.120792, -14.203469]     
link = [link1, link2, link3,link4]
f_target = kdl.Frame(kdl.Rotation.RPY(0, 0, yaw), kdl.Vector(target[0], target[1], target[2]))



def draw_axis(ax, scale=1.0, O=np.eye(4), style='-'):
    xaxis = np.array([[0, 0, 0, 1], [scale, 0, 0, 1]]).T
    yaxis = np.array([[0, 0, 0, 1], [0, scale, 0, 1]]).T
    zaxis = np.array([[0, 0, 0, 1], [0, 0, scale, 1]]).T
    xc = O.dot(xaxis)
    yc = O.dot(yaxis)
    zc = O.dot(zaxis) 
    ax.plot(xc[0,:], xc[1,:], xc[2,:], 'r' + style)
    ax.plot(yc[0,:], yc[1,:], yc[2,:], 'g' + style)
    ax.plot(zc[0,:], zc[1,:], zc[2,:], 'b' + style)
    
def draw_links(ax, origin_frame=np.eye(4), target_frame=np.eye(4)):
    x = [origin_frame[0,3], target_frame[0,3]]
    y = [origin_frame[1,3], target_frame[1,3]]
    z = [origin_frame[2,3], target_frame[2,3]]
    ax.plot(x, y, z, linewidth = 3)


def RX(yaw):
    yaw = np.array(yaw)
    return np.array([[1, 0, 0], 
                     [0, math.cos(yaw), -math.sin(yaw)], 
                     [0, math.sin(yaw), math.cos(yaw)]])   
def RY(delta):
    delta = np.array(delta)
    return np.array([[math.cos(delta), 0, math.sin(delta)], 
                     [0, 1, 0], 
                     [-math.sin(delta), 0, math.cos(delta)]])
def RZ(theta):
    theta = np.array(theta)
    return np.array([[math.cos(theta), -math.sin(theta), 0], 
                     [math.sin(theta), math.cos(theta), 0], 
                     [0, 0, 1]])

def TF(rot_axis=None, q=0, dx=0, dy=0, dz=0):
    if rot_axis == 'x':
        R = RX(q)
    elif rot_axis == 'y':
        R = RY(q)
    elif rot_axis == 'z':
        R = RZ(q)
    elif rot_axis == None:
        R = np.array([[1, 0, 0],
                      [0, 1, 0],
                      [0, 0, 1]])
    
    T = np.array([[R[0,0], R[0,1], R[0,2], dx],
                  [R[1,0], R[1,1], R[1,2], dy],
                  [R[2,0], R[2,1], R[2,2], dz],
                  [0, 0, 0, 1]])
    return T

def FK(angle, link):
    base = TF()
    T0 = TF('y', q = angle[0], dy = link[0])
    T0_0 = base.dot(T0)
    T1 = TF('x', q = angle[1], dy = link[1])
    T1_0 = T0_0.dot(T1)
    
    T2 = TF('y', q = angle[2], dz = -link[2])
    T2_1 = T1_0.dot(T2)
    
    T3 = TF('z', q = angle[3], dz = -link[3])
    T3_2 = T2_1.dot(T3)

    
    return base, T0_0, T1_0, T2_1, T3_2

def objective_function(thetas, link):
    P = FK(thetas, link)
    end_to_target = target - P[-1][:3, 3]
    fitness = math.sqrt(end_to_target[0] ** 2 + end_to_target[1] ** 2 + end_to_target[2] ** 2 )
    return fitness, thetas

def obj_func (thetas, link):
    _,_,_,_,p = FK(thetas,link)
    
    f_result = kdl.Frame(kdl.Rotation(p[0,0], p[0,1], p[0,2],
                                      p[1,0], p[1,1], p[1,2],
                                      p[2,0], p[2,1], p[2,2]),
                         kdl.Vector(p[0,3], p[1,3], p[2,3]))

    f_diff = f_target.Inverse() * f_result
    
    [dx, dy, dz] = f_diff.p
    [drz, dry, drx] = f_diff.M.GetEulerZYX()
    error_pos = np.sqrt(dx**2 + dy**2 + dz**2)
    error_rot = np.sqrt(drz**2)
    error = np.sqrt(dx**2 + dy**2 + dz**2 + drz**2) #pilih yaw aja
    
    return error, thetas,error_pos,error_rot, f_result

Cr=0.5
F=0.5 
NP=20 
max_gen=300
#jumlah yg di inisialisasi
n_params = 4
    
#batas bawah dan atas 
lb = np.array([(-np.radians(60), -np.radians(10), 0 , 0)])
ub = np.array([(np.pi, np.pi/2, (np.radians(160)) , np.pi*2)])

#inisial populasi secara random
target_vectors = np.random.uniform(low=lb, high=ub, size=(NP, n_params))

    
def DE():
    
    donor_vector = np.zeros(n_params)
    trial_vector = np.zeros(n_params)
    ea = []
    best_fitness = np.inf
    list_best_fitness = []
    for gen in range(max_gen):
       # print("Generation :", gen)
        for pop in range(NP):
            #mutasi
            index_choice = [i for i in range(NP) if i != pop]
            index_choice = np.array(index_choice)
            a, b, c = np.random.choice(index_choice, size = 3)
            while a == b or a == c or b == c:
                a, b, c = np.random.choice(index_choice, size =3)
            #print(index_choice)
            #mutasi    
            donor_vector = target_vectors[a] + F * (target_vectors[b]-target_vectors[c])
            #donor_vector = np.clip(donor_vector, lb,ub)
            #donor_vector = donor_vector.flatten()
            #print("donor",donor_vector)
            #crossover
            cross_points = np.random.rand(n_params) < Cr            
            trial_vector = np.where(cross_points, donor_vector, target_vectors[pop])
            #obj_func
            target_fitness, d, err_p,err_r, f_result = obj_func(target_vectors[pop],link)
            trial_fitness, e, err_p,err_r, f_result = obj_func(trial_vector,link)
            
            #seleksi
            if trial_fitness < target_fitness:
                target_vectors[pop] = trial_vector.copy()
                best_fitness = trial_fitness
                angle = e
                #angle = angle.tolist()
            else:
                best_fitness = target_fitness
                angle = d
                #angle = angle.tolist()
    
    #    print("Best fitness :", best_fitness)
        #print(angle)
        
    
       
    return best_fitness, angle, err_p,err_r, f_result



def main():
#    global target, angle, link, yaw
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    fig.suptitle("Differential Evolution - Inverse Kinematics", fontsize=12)
    ax.set_xlim(-100, 100)
    ax.set_ylim(-100, 100)
    ax.set_zlim(-100, 100)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    
    
    
    #Inverse
    err, angle,err_p,err_r, f_r = DE()
    
    if (err > 1): 
       print("IK Error")
    else:
       print("IK Solved")
    
    
    
    #forward Kinematics
    p0, base, p1, p2, p3 = FK(angle,link)
    

    
    [drz, dry, drx] = f_target.M.GetEulerZYX()
    [drz2, dry2, drx2] = f_r.M.GetEulerZYX()
    
    

    angle = np.rad2deg(angle)
    
    angle[3] = angle[3]%(360)
            
 
    draw_axis(ax, scale= 5, O=p0)
    draw_links(ax, origin_frame=p0, target_frame=base)
    draw_axis(ax, scale=5 , O=base)
    draw_links(ax, origin_frame=base, target_frame=p1)
    draw_axis(ax, scale=5, O=p1)
    draw_links(ax, origin_frame=p1, target_frame=p2)
    draw_axis(ax, scale=5, O=p2)
    draw_links(ax, origin_frame=p2, target_frame=p3)
    draw_axis(ax, scale=5, O=p3)
    ax.scatter3D(target[0], target[1], target[2], color = "black", marker = "x")
    print("error", err)    
    print("error pos", err_p)
    print("error rot", err_r)
    print("""""""""""""""""")    
    print("yaw target", drz)
    print("yaw result", drz2)
    print("""""""""""""""""")    
    print("target", target)
    print("end effector", p3[:3,3])
    print("angle", angle)
    print(f"finished after {round(time() - start,2)} seconds")

    plt.show()
    
   
if __name__ == "__main__":
    main()
    
    
    
