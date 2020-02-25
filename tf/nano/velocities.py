import tensorflow as tf
import numpy as np
import math

import utility, common

def initialize_particle_velocities(ion_positions, ion_masses, thermostats):
"""
Numpy implementation to generate random particle starting velocities
Velocities will all be 0 if there is only one (1) thermostat
"""
    if len(thermostats) == 1:
        # start with no velocities
        return np.zeroes(ion_positions.shape, dtype=common.np_dtype) 

    p_sigma = math.sqrt(utility.kB * utility.T / (2.0 * ion_masses[0]))        # Maxwell distribution width

    random_vels = np.random.normal(0, p_sigma, ion_positions.shape)
    avg_vel = np.average(random_vels, axis=0)
    avg_vel = avg_vel * (1/len(ion_positions))
    return random_vels-avg_vel


if __name__ == "__main__":
    positions = np.ones((5,3))
    masses = np.ones(5)
    thms = np.ones(5)
    print(initialize_particle_velocities(positions, masses, thms))