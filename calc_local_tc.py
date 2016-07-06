#!/usr/bin/env python
"""
Usage:
  calc_local_tc.py [options]

Options:
  -i PATH      path to file with sine wave, to be analysed [default: SinWithHighOffset2.dat]
  -c PATH      path to textfile with offsets ala Taka, to be subtracted [default: Ped300Hz_forSine.dat]
  -o PATH      path to outfile for the cell widths [default: local_tc.csv]
  --pixel N    pixel in which the sine wave should be analysed [default: 0]
  --gain NAME  gain type which should be analysed [default: high]
  --fake       use FakeEventGenerator, ignores '-c' and expects '-i' to point to something like local_tc.csv
"""
import dragonboard as dr
import numpy as np
from tqdm import tqdm
from docopt import docopt
import pandas as pd
import matplotlib.pyplot as plt

def calc_local_tc(event_generator, calib, pixel, gain):
    all_slopes = [[] for i in range(1024)]
    stop_cells = np.zeros(1024, dtype=int)

    for event in tqdm(event_generator):
        event = calib(event)
        calibrated = event.data[pixel][gain]
        
        zero_crossings = np.where(np.diff(np.signbit(calibrated)))[0]
        slopes = calibrated[zero_crossings + 1] - calibrated[zero_crossings]
        absolute_slopes = np.abs(slopes)

        sc = event.header.stop_cells[pixel][gain]
        stop_cells[sc%1024] += 1
        zero_crossing_cells = dr.sample2cell(zero_crossings+1, 
            stop_cell=sc,
            total_cells=1024)
        
        for abs_slope, cell_id in zip(absolute_slopes, zero_crossing_cells):
            all_slopes[cell_id].append(abs_slope)

    tc = pd.DataFrame({
            "cell_width_mean": np.zeros(len(all_slopes), dtype=np.float32),
            "cell_width_std": np.zeros(len(all_slopes), dtype=np.float32),
            "number_of_crossings": np.zeros(len(all_slopes), dtype=np.int32),
            "stop_cell": stop_cells,
            "slope_mean": np.zeros(len(all_slopes), dtype=np.float32),
        })
    for cell_id, slopes in enumerate(all_slopes):
        slopes = np.array(slopes)
        tc.loc[cell_id, "number_of_crossings"] = len(slopes)
        tc.loc[cell_id, "cell_width_mean"] = np.mean(slopes) # np.median(slopes)
        tc.loc[cell_id, "slope_mean"] = slopes.mean()
        if False:
            plt.hist(slopes, bins=50, histtype="step")
            plt.title(str(len(slopes)))
            ax = plt.gca()
            ax.ticklabel_format(useOffset=False)
            plt.savefig("slopes/{0:04d}.png".format(cell_id))
            plt.close("all")
        
        tc.loc[cell_id, "cell_width_std"] = slopes.std() / np.sqrt(len(slopes))


    average_of_all_slopes = tc.cell_width_mean.dropna().mean()
    tc["cell_width_mean"] /= average_of_all_slopes
    tc["cell_width_std"]  /= average_of_all_slopes

    return tc


if __name__ == "__main__":
    args = docopt(__doc__)
    pixel = int(args["--pixel"])
    gain = args["--gain"]
    assert gain in ["high", "low"]
    
    if not args["--fake"]:
        event_generator = dr.EventGenerator(args["-i"])
        calib = dr.calibration.TakaOffsetCalibration(args["-c"])
    else:
        from fake_event_gen import FakeEventGenerator
        event_generator = FakeEventGenerator(
            trigger_times=np.arange(10000)* (1/300), # 50k evts at 300Hz
            #trigger_times=np.arange(10000)* (1/300 * (1 + 0e-6)), # 50k evts at 300Hz
            #trigger_times=np.random.uniform(0,1e-9, 10000).cumsum(),
            random_phase=False,
            sine_frequency=30e6 * (1+1e-7),
            cell_width=args["-i"],
        )
        calib = lambda x: x

    tc = calc_local_tc(event_generator, calib, pixel, gain)

    if args["--fake"]:
        tc["cell_width_truth"] = event_generator.cell_widths / event_generator.cell_widths.mean()
     
    tc.to_csv(args["-o"], index=False)