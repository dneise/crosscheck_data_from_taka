#!/usr/bin/env python
"""
Usage:
  calc_local_tc.py [options]

Options:
  -i PATH             path to file with sine wave, to be analysed [default: SinWithHighOffset2.dat]
  -c PATH             path to textfile with offsets ala Taka, to be subtracted [default: Ped300Hz_forSine.dat]
  -o PATH             path to outfile for the cell widths [default: global_tc.csv]
  --local_tc P        path to local_tc.csv file, which can be used as a starting point
  --max_iterations N  maximum number of iterations, after which to stop [default: 10000]
  --pixel N    pixel in which the sine wave should be analysed [default: 0]
  --gain NAME  gain type which should be analysed [default: high]
  --fake       use FakeEventGenerator, ignores '-c' and expects '-i' to point to something like local_tc.csv
"""
import dragonboard as dr
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import time
import pandas as pd
from docopt import docopt


def weight_on_edge(data, zxing):
    """
    This weight is independent of the cell_width. 
    So even, when we have already a good estimation of the cell width, 
    this weight does not need to take the width into account.
    """
    value_before = data[zxing]
    value_after = data[zxing + 1]
    slope = value_after - value_before
    return - value_before / slope



def calc_global_tc(event_generator, calib, pixel, gain, cell_width_guess):
    f_calib = 30e6 # in Hz
    unit_of_ti = 1e-9 # in seconds
    nominal_period = 1 / (f_calib * unit_of_ti)

    cell_width = np.copy(cell_width_guess) 
    T = cell_width.sum()
    stop_cells = np.zeros(1024, dtype=int)

    number_of_zxings_per_cell = np.zeros(1024, dtype=int)

    for event in tqdm(event_generator):
        event = calib(event)
        calibrated = event.data[pixel][gain]
        stop_cell = event.header.stop_cells[pixel][gain]
        stop_cells[stop_cell % 1024] += 1
        zero_crossings = np.where(np.diff(np.signbit(calibrated)))[0]
        number_of_zxings_per_cell[(zero_crossings+stop_cell)%1024] += 1

        for zxing_type in [zero_crossings[0::2], zero_crossings[1::2]]:
            for start, end in zip(zxing_type[:-1], zxing_type[1:]):

                N = end - start + 1
                weights = np.zeros(1024)
                weights[(stop_cell + start + np.arange(N))%1024] = 1.
                weights[(stop_cell + start)%1024] = 1 - weight_on_edge(calibrated, start)
                weights[(stop_cell + end)%1024] = weight_on_edge(calibrated, end)

                measured_period = (weights * cell_width).sum()
                if measured_period < nominal_period*0.7 or measured_period > nominal_period*1.3:
                    continue

                n0 = nominal_period / measured_period
                n1 = (T - nominal_period) / (T - measured_period)

                correction = n0 * weights + n1 * (1-weights)
                cell_width *= correction

                # The next line is fishy:
                #   * it should not be possibl to have a width < 0, but Ritt has shown it is.
                #   * cells more than double their nominal size, seem impossible, but one cell with 200% width
                #       can easily be accomplished with 10 cells having only 90% their nominal width.
                #  Never the less, without this line, the result can become increadibly shitty!
                cell_width = np.clip(cell_width, 0, 2)  
                cell_width /= cell_width.mean()


    # Regarding the uncertainty of the cell width, we assume that the correction should become
    # smaller and smaller, the more interations we perform.
    # so the last corrections should be very close to 1. 

    tc = pd.DataFrame({
        "cell_width_mean": np.roll(cell_width, 1),
        "cell_width_std": np.zeros(1024),  # np.full((len(cell_width), np.nan)
        "number_of_crossings": number_of_zxings_per_cell,
        "stop_cell": stop_cells,
        })
    return tc



if __name__ == "__main__":
    args = docopt(__doc__)
    args["--max_iterations"] = int(args["--max_iterations"])
    pixel = int(args["--pixel"])
    gain = args["--gain"]
    assert gain in ["high", "low"]
    
    if not args["--fake"]:
        event_generator = dr.EventGenerator(
            args["-i"], 
            max_events=args["--max_iterations"],
        )
        calib = dr.calibration.TakaOffsetCalibration(args["-c"])
    else:
        from fake_event_gen import FakeEventGenerator
        event_generator = FakeEventGenerator(
            trigger_times=np.arange(10000) * (1/300), # 50k evts at 300Hz
            #trigger_times=np.random.uniform(0,1e-9, 10000).cumsum(),
            random_phase=False,
            sine_frequency=30e6 * (1+1e-7),
            cell_width=args["-i"],
        )
        calib = lambda x: x

    if not args["--local_tc"]:
        cell_width_guess=np.ones(1024)
    else:
        cell_width_guess=pd.read_csv(args["--local_tc"])["cell_width_mean"].values

    tc = calc_global_tc(
        event_generator, 
        calib, 
        pixel, 
        gain, 
        cell_width_guess)


    if args["--fake"]:
        tc["cell_width_truth"] = event_generator.cell_widths / event_generator.cell_widths.mean()
     
    tc.to_csv(args["-o"], index=False)

