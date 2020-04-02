import tensorflow as tf
import numpy as np
import utility, common

_therm_constants = []

def to_string(therm_dict):
    return "xi:{}, eta:{}".format(therm_dict["xi"],therm_dict["eta"])

def create_thermostat(i, Q: float, T: float, dof: float, xi: float, eta: float, hold: float):
    _therm_constants.append({"Q": Q, "T": T, "dof": dof, "hold": hold})
    return {"xi":xi, "eta":eta}

def get_placeholders(therms):
    ret = []
    ret_copy = []
    for value in therms:
        place, copy = common.make_tf_placeholder_of_dict(value)
        ret.append(place)
        ret_copy.append(copy)
    return ret, ret_copy

def therms_to_feed_dict(therms, therms_place):
    feed = {}
    for therm_key, therm_value in enumerate(therms):
        for key, value in therm_value.items():
            feed[therms_place[therm_key][key]] = value
    return feed

def make_thremostats(chain_length_real, ions_count):
    Q = 1.0  # thremostat mass
    therms = []
    i=0
    if (chain_length_real == 1):
        therms.append(create_thermostat(i=i, Q=0.0, T=utility.T, dof=3* ions_count, xi=0.0, eta=0.0, hold=0.0))
    else:
        therms.append(create_thermostat(i=i, Q=Q, T=utility.T, dof=3 * ions_count, xi=0.0, eta=0.0, hold=0.0))
        i += 1
        while (len(therms) != chain_length_real - 1):
            therms.append(create_thermostat(i=i, Q=Q / (3 * ions_count), T=utility.T, dof=1.0, xi=0.0, eta=0.0, hold=0.0))
            i += 1
        # final therms is dummy therms (dummy therms always has zero mass)
        therms.append(create_thermostat(i=i, Q=0.0, T=utility.T, dof=3 * ions_count, xi=0.0, eta=0.0, hold=0.0))
    print("_therm_constants", _therm_constants)
    return therms

def update_xi_at(therms, j, dt, ke):
    if _therm_constants[j]["Q"] == 0:
        return therms
    # print("therm", j)
    if (j != 0):
        therms[j]["xi"] = therms[j]["xi"] * tf.math.exp(-0.5 * dt * therms[j + 1]["xi"]) + 0.5 * dt * (1.0 / _therm_constants[j]["Q"]) *\
            (_therm_constants[j - 1]["Q"] * therms[j - 1]["xi"] * therms[j - 1]["xi"] -
             _therm_constants[j]["dof"] * utility.kB * _therm_constants[j]["T"]) *\
                                                tf.math.exp(-0.25 * dt * therms[j + 1]["xi"])
    else:
        therms[j]["xi"] = therms[j]["xi"] * tf.math.exp(-0.5 * dt * therms[j + 1]["xi"]) +\
            (0.5 * dt * (1.0 / _therm_constants[j]["Q"]) * (2 * ke - _therm_constants[j]["dof"] * utility.kB * _therm_constants[j]["T"]) *
                    tf.math.exp(-0.25 * dt * therms[j + 1]["xi"]))
    return therms

def reverse_update_xi(therms, dt: float, ke):
    with tf.name_scope("reverse_update_xi"):
        for j in range(len(therms)-1, -1, -1):
            therms = update_xi_at(therms, j, dt, ke)
        return therms
    
def forward_update_xi(therms, dt: float, ke):
    with tf.name_scope("forward_update_xi"):
        for j in range(0, len(therms)):
            therms = update_xi_at(therms, j, dt, ke)
        return therms        

# returns full therms dictionary with updated eta tensor
def update_eta(therms, dt: float):
    with tf.name_scope("update_eta"):
        for j in range(0, len(therms)):
            if _therm_constants[j]["Q"] == 0:
                continue
            therms[j]["eta"] = therms[j]["eta"] + (0.5 * dt * therms[j]["xi"])
        return therms

def calc_exp_factor(therms, dt):
    return tf.math.exp(-0.5 * dt * therms[0]["xi"])

if __name__ == "__main__":
    r = make_thremostats(5, 5)
    print(len(r),r)
    r_place, r_names = get_placeholders(r)

    print("\n\n", r_place)
    feed = therms_to_feed_dict(r, r_names)
    print(feed, "\n\n")
    x = reverse_update_xi(r_place, 0.01, 200.81)
    x = update_eta(x, 0.01)
    x = forward_update_xi(x, 0.01, 200.81)
    print("\n result", x[0]["xi"])
    print(feed)
    sess = tf.compat.v1.Session()
    sess.as_default()
    out = sess.run(x, feed_dict=feed)
    print(out, "\n")
    ft = therms_to_feed_dict(out, r_names)
    out = sess.run(x, feed_dict=ft)
    print(out, "\n")
    ft = therms_to_feed_dict(out, r_names)
    out = sess.run(x, feed_dict=ft)
    print(out, "\n")
