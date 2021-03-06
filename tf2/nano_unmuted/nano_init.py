import tensorflow as tf
import numpy as np
import argparse, math, os, datetime

import utility, control, interface, bin, thermostat, md, velocities, forces, common
import tensorflow_manip as tfmanip

np.random.seed(0) # be consistent
# import sys
# np.set_printoptions(threshold=sys.maxsize)

def start_sim(tf_sess_config, args):
    utility.root_path = os.path.join("output/", datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    os.makedirs(utility.root_path)
    negative_diameter_in = args.neg_diameter
    positive_diameter_in = args.pos_diameter
    charge_density = args.charge_density
    if (positive_diameter_in <= negative_diameter_in):
        utility.unitlength = positive_diameter_in
        smaller_ion_diameter = positive_diameter_in
        bigger_ion_diameter = negative_diameter_in
    else:
        utility.unitlength = negative_diameter_in
        smaller_ion_diameter = negative_diameter_in
        bigger_ion_diameter = positive_diameter_in

    utility.unittime = math.sqrt(utility.unitmass * utility.unitlength * pow(10.0, -7) * utility.unitlength / utility.unitenergy)
    utility.scalefactor = utility.epsilon_water * utility.lB_water / utility.unitlength
    bz = args.confinment_len
    salt_conc_in = args.concentration
    bx = math.sqrt(212 / 0.6022 / salt_conc_in / bz)
    by = bx
    # print(str(bx), " ", str(by)," ",)
    if (charge_density < -0.01 or charge_density > 0.0): # we can choose charge density on surface between 0.0 (uncharged surfaces)  to -0.01 C/m2.
        print("\ncharge density on the surface must be between zero to -0.01 C/m-2 aborting\n")
        exit(1)
    pz_in = args.pos_valency
    valency_counterion = 1 #pz_in
    counterion_diameter_in = positive_diameter_in
    surface_area = bx * by * pow(10.0, -18)  # in unit of squared meter
    number_meshpoints = pow((1.0 / args.fraction_diameter), 2.0)
    charge_meshpoint = (charge_density * surface_area) / (utility.unitcharge * number_meshpoints)
    # in unit of electron charge
    total_surface_charge = charge_meshpoint * number_meshpoints  # in unit of electron charge
    print("DEBUG:: total_surface_charge:", total_surface_charge)
    counterions =  2.0 * (int(abs(total_surface_charge)/valency_counterion)) # there are two charged surfaces, we multiply the counter ions by two
    # counterions = 0
    print("Counterions:", counterions)
    nz_in = args.neg_valency

    # we should make sure the total charge of both surfaces and the counter ions are zero
    if (((valency_counterion * counterions) + (total_surface_charge * 2.0 )) != 0):
        # we distribute the extra charge to the mesh points to make the system electroneutral then we recalculate the charge density on surface
        charge_meshpoint = -1.0 * (valency_counterion * counterions) / (number_meshpoints * 2.0)
        total_surface_charge = charge_meshpoint * number_meshpoints # we recalculate the total charge on teh surface
        charge_density = (total_surface_charge * utility.unitcharge) / surface_area # in unit of Coulomb per squared meter
    mdremote = control.Control(args)

    if (mdremote.steps < 100000):      # minimum mdremote.steps is 20000
        mdremote.hiteqm = int(mdremote.steps*0.1)
        mdremote.writedensity =int(mdremote.steps*0.1)
        mdremote.extra_compute = int(mdremote.steps*0.01)
        mdremote.moviefreq = int(mdremote.steps*0.001)
    else:
        mdremote.hiteqm = int(mdremote.steps * 0.2)
        mdremote.writedensity = int(mdremote.steps * 0.1)
        mdremote.extra_compute = int(mdremote.steps * 0.01)
        mdremote.moviefreq = int(mdremote.steps * 0.001)

    if mdremote.extra_compute == 0:
        mdremote.extra_compute=1

    if mdremote.writedensity == 0:
        mdremote.writedensity = 1

    if mdremote.hiteqm == 0:
        mdremote.hiteqm = 1
    if mdremote.moviefreq == 0:
        mdremote.moviefreq = 1
    T=1
    simul_box = interface.Interface(salt_conc_in=salt_conc_in, salt_conc_out=0, salt_valency_in=pz_in, salt_valency_out=0, bx=bx/utility.unitlength, by=by/utility.unitlength, bz=bz/utility.unitlength, \
        initial_ein=mdremote.ein, initial_eout=mdremote.eout)
    ion_dict = simul_box.put_saltions_inside(pz=pz_in, nz=nz_in, concentration=salt_conc_in, positive_diameter_in=positive_diameter_in, \
                                            negative_diameter_in=negative_diameter_in, counterions=counterions, valency_counterion=valency_counterion, \
                                            counterion_diameter_in=counterion_diameter_in, bigger_ion_diameter=bigger_ion_diameter, crystal_pack=args.random_pos_init)

    simul_box.discretize(smaller_ion_diameter / utility.unitlength, args.fraction_diameter, charge_meshpoint)
    bins = bin.make_bins(simul_box, args.bin_width)

    #TODO: write initial densities
    thermos = thermostat.make_thermostats(args.chain_length_real, ions_count=len(ion_dict[interface.ion_pos_str]), Q=args.therm_mass)
    
    ion_dict = velocities.initialize_particle_velocities(ion_dict, thermos)
    ion_dict = forces.for_md_calculate_force(simul_box, ion_dict, charge_meshpoint)   #forces.initialize_forces(ion_dict)
    
    md.run_md_sim(simul_box, thermos, ion_dict, charge_meshpoint, valency_counterion, mdremote, bins)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c',"--cpu", action="store_true")
    parser.add_argument('-v',"--verbose", action="store_true")
    parser.add_argument('-x', "--xla", action="store_true")
    parser.add_argument('-r', "--prof", action="store_true")
    parser.add_argument('-o', "--opt", action="store_true")
    parser.add_argument('-M', "--concentration", action="store", default=0.50, type=float)
    parser.add_argument('-e', "--pos-valency", action="store", default=1, type=int)  #changed from 1 to 0
    parser.add_argument('-en', "--neg-valency", action="store", default=-1, type=int)  #changed from -1 to 0
    parser.add_argument('-cl', "--confinment-len", action="store", default=3.0, type=float)
    parser.add_argument('-pd', "--pos-diameter", action="store", default=0.714, type=float)
    parser.add_argument('-nd', "--neg-diameter", action="store", default=0.714, type=float)
    parser.add_argument('-d', "--charge-density", action="store", default=0.00, type=float)
    parser.add_argument("--ein", action="store", default=80, type=float)
    parser.add_argument("--eout", action="store", default=80, type=float)
    # parser.add_argument('-ec', "--extra-compute", action="store", default=10000, type=int)
    parser.add_argument('-t', "--delta-t", action="store", default=0.0005, type=float)
    parser.add_argument('-s', "--steps", action="store", default=100, type=int)
    parser.add_argument('-f', "--freq", action="store", default=1, type=int)
    parser.add_argument("--threads", action="store", default=os.cpu_count(), type=int)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--random-pos-init", action="store_false")
    parser.add_argument('-bw', "--bin_width", action="store", default=0.05, type=float)
    parser.add_argument('-fd', "--fraction_diameter", action="store", default= 0.02, type=float)
    parser.add_argument('-chl',"--chain_length_real", action="store", default=5, type=float)
    parser.add_argument('-Q', "--therm_mass", action="store", default=1.0, type=float)
    args = parser.parse_args()

    tfmanip.toggle_xla(args.xla)
    tfmanip.manual_optimizer(args.opt)
    config = tfmanip.toggle_cpu(args.cpu, args.threads)
    tfmanip.silence()
    start_sim(config, args)
