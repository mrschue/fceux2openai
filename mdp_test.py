from __future__ import print_function
import fceux_gym
import mdp
from time import sleep
import numpy as np
import math

n_actions = 500
n_rounds = 6
noise_std = 2
batch_size = 125

size_groups = 20
reordering = False

#hsfa_node = mdp.nodes.HSFANode((240, 256), [(6, 8), (4, 4), (4, 4), (-1, -1)], [(4, 4), (2, 2), (2, 2), (-1, -1)],
#                              [50, 30, 20, 20], 1)
hsfa_node = mdp.nodes.HSFANode((240, 256), [(6,8), (2,2), (2,2), (2,2), (2,2), (-1,-1)], [(3,4), (1,1), (1,1), (1,1), (1,1), (-1,-1)], [40, 20, 10, 10, 10, 12], 1)

nr_batches = math.ceil(n_actions / float(batch_size))

env = mdp.nodes.GymNode("NESMM2Boss-v0", auto_reset=True)
observation_switchboard = mdp.hinet.Switchboard(2*env.observation_dim+3, range(0, env.observation_dim))

mm_out = np.memmap("memmap_object.mm", dtype="float32", mode="w+", shape=(n_actions, 2*env.observation_dim+3))



print("Training HSFA")
n_layers = hsfa_node.get_remaining_train_phase()
for p in range(hsfa_node.get_remaining_train_phase()):
    print("Layer  "+str(p+1)+" of "+str(n_layers))
    for round in range(n_rounds):
        print("\tRound "+str(round+1))
        print("\tExecuting random actions")
        a = env.get_random_actions(n_actions)
        mm_out[:] = env.execute(a)[:]

        output = observation_switchboard(mm_out)

        print("\tAdding Noise")
        for i in range(output.shape[0]):
            output[i] += np.random.randn(output.shape[1], ).T * noise_std

        if reordering:
            print("\tRearranging")
            n_groups = n_actions / size_groups
            random_order = np.random.permutation(n_groups)
            reorder_indices = []
            for r in random_order:
                reorder_indices += list(range(r * size_groups, r * size_groups + size_groups))
            output = output[reorder_indices]

        print("\tTraining")
        print("\t Batch: ", end="")
        for batch_idx in range(nr_batches):
            print(str(batch_idx+1)+"..", end="")
            hsfa_node.train(output[batch_idx*batch_size:batch_idx*batch_size+batch_size])
        print("\n\t----")
    hsfa_node.stop_training()


sfa_viz = mdp.nodes.PGCurveNode(split_figs=True, use_buffer=True, x_range=(0,100), y_range=(-5,5))
mm_viz = mdp.nodes.PGImageNode((240, 256), axis_order="row-major", origin='lower')

new_input = True

if new_input:
    while (True):
        a = env.get_random_actions(1)
        obs = observation_switchboard(env.execute(a))
        o = hsfa_node.execute(obs)
        sfa_viz.execute(o)
        sleep(0.01)

else:
    print("Visualizing")
    for i in range(output.shape[0]-2):
        mm_viz.execute(output[i, None])
        o = hsfa_node.execute(output[i, None])
        sfa_viz.execute(o)
        sleep(0.08)

#for i in range(0, 0):
#    a = env.get_random_actions(1)
#    output = env.execute(a)
#    obs = observation_switchboard.execute(output)
#    reward = output[:, 2*env.observation_dim + 1]
#    done = output[:, 2*env.observation_dim + 2]
#    if reward[0] != 0:
#        print(reward[0])
#    if done[0]:
#        print("- Episode done! -")

    ############
