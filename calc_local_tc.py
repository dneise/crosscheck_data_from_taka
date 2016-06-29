"""
Usage:
  calc_local_tc.py [options]

Options:
  -i PATH      path to file with sine wave, to be analysed [default: SinWithHighOffset2.dat]
  -c PATH      path to textfile with offsets ala Taka, to be subtracted [default: Ped300Hz_forSine.dat]
  -o PATH      path to outfile for the cell widths [default: local_tc.csv]
  --pixel N    pixel in which the sine wave should be analysed [default: 0]
  --gain NAME  gain type which should be analysed [default: high] 
"""
import dragonboard as dr
import numpy as np
from tqdm import tqdm
from docopt import docopt
import pandas as pd


args = docopt(__doc__)
print(args)
event_generator = dr.EventGenerator(args["-i"])
calib = dr.calibration.TakaOffsetCalibration(args["-c"])

pixel = int(args["--pixel"])
gain = args["--gain"]
assert gain in ["high", "low"]


all_slopes = [[] for i in range(1024)]

for event in tqdm(event_generator):
    event = calib(event)
    calibrated = event.data[pixel][gain]
    
    zero_crossings = np.where(np.diff(np.signbit(calibrated)))[0]
    slope = calibrated[zero_crossings + 1] - calibrated[zero_crossings]

    zero_crossing_cells = dr.sample2cell(zero_crossings, 
        stop_cell=event.header.stop_cells[pixel][gain], 
        total_cells=1024)
    
    for crossing_number, cell_id in enumerate(zero_crossing_cells):
        all_slopes[cell_id].append(np.abs(slope[crossing_number]))

slope_mean = np.zeros(1024)
slope_std = np.zeros(1024)
for cell_id, slopes in enumerate(all_slopes):
    slopes = np.array(slopes)
    slope_mean[cell_id] = slopes.mean()
    slope_std[cell_id] = slopes.std() / np.sqrt(len(slopes))

pd.DataFrame({
    "cell_width_mean": slope_mean / slope_mean.mean(),
    "cell_width_std": slope_std /  slope_mean.mean(),
    }
    ).to_csv(args["-o"], index=False)

