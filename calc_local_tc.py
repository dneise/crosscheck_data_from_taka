"""
Usage:
  calc_local_tc.py [options]

Options:
  -i PATH      path to file with sine wave, to be analysed [default: SinWithHighOffset2.dat]
  -c PATH      path to textfile with offsets ala Taka, to be subtracted [default: Ped300Hz_forSine.dat]
  -o PATH      path to outfile for the cell widths [default: local_tc.csv]
  --pixel N    pixel in which the sine wave should be analysed [default: 0]
  --gain NAME  gain type which should be analysed [default: high]
  --fake       use FakeEventGenerator, ignores '-i' and '-c'.
"""
import dragonboard as dr
import numpy as np
from tqdm import tqdm
from docopt import docopt
import pandas as pd

def calc_local_tc(event_generator, calib, pixel, gain):
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

    tc = pd.DataFrame({
            "cell_width_mean": np.zeros(len(all_slopes), dtype=np.float32),
            "cell_width_std": np.zeros(len(all_slopes), dtype=np.float32),
            "number_of_crossings": np.zeros(len(all_slopes), dtype=np.int32),
        })    
    for cell_id, slopes in enumerate(all_slopes):
        slopes = np.array(slopes)
        tc.loc[cell_id, "number_of_crossings"] = len(slopes)
        tc.loc[cell_id, "cell_width_mean"] = slopes.mean()
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
        event_generator = FakeEventGenerator(trigger_times=np.random.uniform(0, 1e-8, 10000).cumsum())
        calib = lambda x: x

    tc = calc_local_tc(event_generator, calib, pixel, gain)

    if args["--fake"]:
        tc["cell_width_truth"] = event_generator.cell_widths / event_generator.cell_widths.mean()
     
    tc.to_csv(args["-o"], index=False)