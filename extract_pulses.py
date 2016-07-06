"""
Usage:
  extract_pulses.py [options]

Options:
  --input PATH    path to file containing test pulses [default: LnG40.dat]
  --offset PATH   path to textfile with offset ala Taka [default: Ped300Hz.dat]
  --tc PATH       path to csv containting cell_widths [default: local_tc.csv]
  --channel N     channel number to be analyszed [default: 0]
  --gain NAME     name of gain_type to be analysed. high/low [default: high]
  --maxevents N   number of events to be used [default: 20000]
  --int_window N  size of integration window [default: 7]
"""
import dragonboard as dr
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm as progress_bar
import time
import pandas as pd
from docopt import docopt
from scipy.interpolate import interp1d
from matplotlib.colors import LogNorm
import hist2d
from functools import partial
import scipy


def digital_leading_edge_discriminator(data, time, threshold=0, window_length=0):
    z = np.where(np.diff(np.signbit(data-threshold)))[0][0]
    if window_length == 0:  
        # There is no data to fit, so we simply do it by and ... saving time.
        time_before = time[z]
        time_after = time[z+1]
        value_before = data[z]
        value_after = data[z+1]

        slope = (value_after - value_before)/(time_after - time_before)

        # value = value_before + delta_time * slope
        # threshold = value_before + delta_time_0 * slope
        delta_time_0 = (threshold - value_before) / slope
        return time_before + delta_time_0
    else:
        s = slice(z-window_length, z+2+window_length)
        m, b = np.polyfit(time[s], data[s], deg=1)
        return (threshold-b)/m

args = docopt(__doc__)
args["--channel"] = int(args["--channel"])
args["--int_window"] = int(args["--int_window"])

assert args["--gain"] in ["high", "low"]
try:
    args["--maxevents"] = int(args["--maxevents"])
except ValueError:
    args["--maxevents"] = None
print(args)


cell_width = pd.read_csv(args["--tc"])["cell_width_mean"].values
template_orig = pd.read_csv("pulse_dataframe.csv")
template = template_orig["pulse_mode"].values[60:180]
template /= template.max()

tc_base_name = args["--tc"][:-4]

offset = np.genfromtxt(args["--offset"])[:,0]
# trick to omit np.roll
offset = np.concatenate((offset, offset))
cell_width = np.concatenate([cell_width]*5)

# for midpoint_rule each sample v_i gets mutiplied with 1/2 * (d_{i-1} + d_i)
midpoint_width = 1/2 * (cell_width + np.roll(cell_width, -1))

half_integration_window = (args["--int_window"] - 1) // 2


ch = args["--channel"]
gain = args["--gain"]



run = dr.EventGenerator(args["--input"], max_events=args["--maxevents"])
NN = min(len(run), args["--maxevents"])

integral = np.zeros(NN, dtype='f4')
integral_weighted = np.zeros(NN, dtype='f4')
max_pos = np.zeros(NN, dtype='i4')
arrival_time = np.zeros(NN, dtype='f4')
arrival_time_no_calib = np.zeros(NN, dtype='f4')
trapz = np.zeros(NN, dtype='f4')
simps = np.zeros(NN, dtype='f4')

for i, event in enumerate(progress_bar(run, leave=True)):
    raw_data = event.data[ch][gain]
    stop_cell = event.header.stop_cells[ch][gain]
    calibrated = raw_data - offset[stop_cell:stop_cell+run.roi]
    t = cell_width[stop_cell:stop_cell+run.roi].cumsum()

    max_pos[i] = np.argmax(calibrated)

    s = slice(max_pos[i]-half_integration_window, max_pos[i]+half_integration_window+1)
    samples = np.arange(s.start, s.stop)
    cells = dr.sample2cell(samples, stop_cell, total_cells=1024)    
    DLE = partial(digital_leading_edge_discriminator, data=calibrated, threshold=1000)

    arrival_time[i] = DLE(time=t)
    arrival_time_no_calib[i] = DLE(time=np.arange(len(calibrated)))
    integral[i] = calibrated[s].sum()
    integral_weighted[i] = (calibrated[s] * midpoint_width[cells]).sum()
    trapz[i] = np.trapz(calibrated[s], t[s])
    simps[i] = scipy.integrate.simps(calibrated[s], t[s])


df = pd.DataFrame({
    "integral": integral, 
    "integral_weighted": integral_weighted, 
    "max_pos": max_pos, 
    "arrival_time": arrival_time, 
    "arrival_time_no_calib": arrival_time_no_calib, 
    "trapz": trapz,
    "simps": simps,
})
    
plt.figure()
names=["integral", "integral_weighted", "trapz", "simps"]
for name in names: 
    rel_width_in_percent =  df[name].std()/df[name].mean() * 100
    plt.hist(df[name], bins=np.arange(3500, 6500, 20), histtype="step", log=False, label="{0}:$\sigma$={1:.1f}%".format(name, rel_width_in_percent))
plt.grid()
plt.legend(loc="best")
plt.xlabel("charge [a.u.]")
plt.title("Charge Resolution with {}".format(tc_base_name))
plt.savefig("charge_resolution_{}.png".format(tc_base_name))

plt.figure()
names = ["max_pos", "arrival_time", "arrival_time_no_calib"]
for name in names:
    width_in_ns =  df[name].std()
    plt.hist(df[name], bins=np.linspace(50, 65, 76), histtype="step", log=False, label="{0}:$\sigma$={1:.3f}ns".format(name, width_in_ns))
plt.grid()
plt.legend(loc="best")
plt.xlabel("time [ns]")
plt.title("Time Resolution with {}".format(tc_base_name))
plt.savefig("time_resolution_{}.png".format(tc_base_name))