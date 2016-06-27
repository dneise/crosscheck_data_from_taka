"""
Usage:
  extract_pulses.py [options]

Options:
  --input PATH    path to file containing test pulses [default: LnG40.dat]
  --offset PATH   path to textfile with offset ala Taka [default: Ped300Hz.dat]
  --tc PATH       path to csv containting cell_widths [default: local_tc.csv]
  --channel N     channel number to be analyszed [default: 0]
  --gain NAME     name of gain_type to be analysed. high/low [default: high]
  --maxevents N   number of events to be used [default: all]
  --int_window N  size of integration window [default: 5]
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

def digital_leading_edge_discriminator(data, time, threshold=0, window_length=0):
    z = np.where(np.diff(np.signbit(data-threshold)))[0][0]
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


cell_width = pd.read_csv(args["--tc"])["cell_width"].values
template = pd.read_csv("pulse_dataframe.csv")
template = template["pulse_mode"].values[60:180]
template /= template.max()


run = dr.EventGenerator(args["--input"], max_events=args["--maxevents"])
offset = np.genfromtxt(args["--offset"])[:,0]
# trick to omit np.roll
offset = np.concatenate((offset, offset))
cell_width = np.concatenate([cell_width]*5)
cell_width = np.roll(cell_width, 1)

df = []
half_integration_window = (args["--int_window"] - 1) // 2


ch = args["--channel"]
gain = args["--gain"]

for event in progress_bar(run, leave=True):
    raw_data = event.data[ch][gain]
    stop_cell = event.header.stop_cells[ch][gain]
    
    calibrated = raw_data - offset[stop_cell:stop_cell+run.roi]
    t = cell_width[stop_cell:stop_cell+run.roi].cumsum()

    # pulse_template and new_values should have the same spacing
    interpolant = interp1d(t, calibrated)
    new_times = np.linspace(50, 90, 401)
    new_values = interpolant(new_times)

    conv = np.convolve(new_values, template, mode="valid")
    time_of_max_convolution = new_times[conv.argmax()]

    arrival_time = digital_leading_edge_discriminator(data=calibrated, time=t, threshold=1000)
    arrival_time_no_calib = digital_leading_edge_discriminator(data=calibrated, time=np.arange(len(calibrated)), threshold=1000)

    max_pos = np.argmax(calibrated)
    s = slice(max_pos-half_integration_window, max_pos+half_integration_window)
    integral = (calibrated[s]).sum()
    
    samples = np.arange(s.start, s.stop)
    cells = dr.sample2cell(samples, stop_cell, total_cells=1024)
    weights = cell_width[cells]
        
    integral_weighted = (calibrated[s] * weights).sum()
    
    interpolated_integral = np.trapz(new_values, new_times)

    df.append((
        max_pos,
        integral,
        integral_weighted,
        arrival_time,
        arrival_time_no_calib,
        interpolated_integral,
        time_of_max_convolution,
        conv.max()
        ))

df = pd.DataFrame(df, columns=[
        "max_pos",
        "integral",
        "integral_weighted",
        "arrival_time",
        "arrival_time_no_calib",
        "interpolated_integral",
        "time_of_max_convolution",
        "conv",
    ])
df["conv"] /= df.conv.mean()
df["conv"] *= 5000

tc_name = args["--tc"][:-4]

plt.figure()
names=["integral", "integral_weighted", "interpolated_integral", "conv"]
for name in names: 
    rel_width_in_percent =  df[name].std()/df[name].mean() * 100
    plt.hist(df[name], bins=np.arange(3500, 6500, 20), histtype="step", log=False, label="{0}:$\sigma$={1:.1f}%".format(name, rel_width_in_percent))
plt.grid()
plt.legend()
plt.xlabel("charge [a.u.]")
plt.title("Charge Resolution")
plt.savefig("charge_resolution_{}.png".format(tc_name))

plt.figure()
names = ["arrival_time", "arrival_time_no_calib","time_of_max_convolution"]
for name in names:
    width_in_ns =  df[name].std()
    plt.hist(df[name], bins=np.linspace(50, 65, 76), histtype="step", log=False, label="{0}:$\sigma$={1:.3f}ns".format(name, width_in_ns))

plt.grid()
plt.legend()
plt.xlabel("time [ns]")
plt.title("Time Resolution")
plt.savefig("time_resolution_{}.png".format(tc_name))