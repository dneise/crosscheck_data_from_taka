"""
Usage:
  extract_pulses.py [options]

Options:
  --input PATH    path to file containing test pulses [default: LnG40.dat]
  --offset PATH   path to textfile with offset ala Taka, to be subtracted [default: Ped300Hz.dat]
  --tc PATH       path to csv containting cell_widths [default: local_tc.csv]
  --channel N     channel number to be analyszed [default: 0]
  --gain NAME     name of gain_type to be analysed. high/low [default: high]
  --maxevents N   number of events to be used [default: all]
  --png_out PATH  path to png, which should be saved [default: pulse_template.png]  
  --csv_out PATH  path to csv, which should be saved [default: pulse_dataframe.csv]
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


assert args["--gain"] in ["high", "low"]
try:
    args["--maxevents"] = int(args["--maxevents"])
except ValueError:
    args["--maxevents"] = None
print(args)

cell_width = pd.read_csv(args["--tc"])["cell_width"].values
run = dr.EventGenerator(args["--input"], max_events=args["--maxevents"])
offset = np.genfromtxt(args["--offset"])[:,0]
# trick to omit np.roll
offset = np.concatenate((offset, offset))
cell_width = np.concatenate([cell_width]*5)
cell_width = np.roll(cell_width, 1)


ch = args["--channel"]
gain = args["--gain"]



bins = [np.linspace(50, 80, 301), np.linspace(-500, 2500, 601)]
histo, _, _ = np.histogram2d([],[], bins=bins)

for event in progress_bar(run, leave=True):
    raw_data = event.data[ch][gain]
    stop_cell = event.header.stop_cells[ch][gain]
    
    calibrated = raw_data - offset[stop_cell:stop_cell+run.roi]
    t = cell_width[stop_cell:stop_cell+run.roi].cumsum()
    h, _, _ = np.histogram2d(t, calibrated, bins=bins)
    histo += h




# normalize histo along y
histo /= histo.mean(axis=1)[:, np.newaxis]


plt.figure()
plt.imshow(
    histo.T, 
    cmap="viridis", 
    interpolation="nearest", 
    origin="lower",
    extent=(bins[0][0], bins[0][-1], bins[1][0], bins[1][-1]),  # (left, right, bottom, top)
    aspect="auto",
    norm=LogNorm(),
)

HH = hist2d.Hist2d(histo, bins[0], bins[1])

bin_center, pulse_mean = hist2d.profile_along_x(HH, method="mean")
bin_center, pulse_std = hist2d.profile_along_x(HH, method="std")
bin_center, pulse_mode = hist2d.profile_along_x(HH, method="mode")
plt.plot(bin_center, pulse_mean, 'r-', lw=4, label="mean")
plt.errorbar(x=bin_center, y=pulse_mean, yerr=pulse_std, fmt='.', color="r")
plt.plot(bin_center, pulse_mode, 'y-', lw=4, label="mode")
plt.grid()
plt.legend()
plt.xlabel("time [ns]")
plt.ylabel("voltage [a.u.]")
plt.title("Pulse template for charge extraction and arrival time")
plt.savefig(args["--png_out"])

pulse = pd.DataFrame({
    "bin_center": bin_center, 
    "pulse_mean": pulse_mean, 
    "pulse_mode": pulse_mode, 
    "pulse_std": pulse_std,
    })
pulse.to_csv(args["--csv_out"], index=False)
