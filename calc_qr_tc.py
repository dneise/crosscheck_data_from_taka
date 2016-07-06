#!/usr/bin/env python
"""
Usage:
  calc_qr_tc.py [options]

Options:
  -i PATH             path to file with sine wave, to be analysed [default: SinWithHighOffset2.dat]
  -c PATH             path to textfile with offsets ala Taka, to be subtracted [default: Ped300Hz_forSine.dat]
  -o PATH             path to outfile for the cell widths [default: qr_tc.csv]
  --local_tc P        path to local_tc.csv file, which can be used as a starting point
  --max_iterations N  maximum number of iterations, after which to stop [default: 7000]
  --pixel N    pixel in which the sine wave should be analysed [default: 0]
  --gain NAME  gain type which should be analysed [default: high]
  --fake       use FakeEventGenerator, ignores '-i' and '-c'.
"""
import dragonboard as dr
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import time
import pandas as pd
from docopt import docopt
from scipy.sparse import lil_matrix, csr_matrix, csc_matrix
from numpy.linalg import matrix_rank
from scipy.sparse.linalg import lsqr, lsmr, svds
import matplotlib.pyplot as plt



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



def calc_qr_tc(event_generator, calib, pixel, gain, cell_width_guess):
    f_calib = 30e6 # in Hz
    unit_of_ti = 1e-9 # in seconds
    nominal_period = 1 / (f_calib * unit_of_ti)

    cell_width = np.copy(cell_width_guess) 
    T = cell_width.sum()
    stop_cells = np.zeros(1024, dtype=int)
    number_of_zxings_per_cell = np.zeros(1024, dtype=int)

    weight_matrix = []
    for event_id, event in enumerate(tqdm(event_generator)):
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
                if weights.sum() < 30:
                    continue
                weight_matrix.append(weights[:])        

    csr = csr_matrix(weight_matrix)
    cell_width = lsqr(csr, np.ones(csr.shape[0])*1000/30)[0]

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
            trigger_times=np.arange(args["--max_iterations"])* (1/300), # 50k evts at 300Hz
            random_phase=True,
            sine_frequency=30e6,
            cell_width=args['-i'],
            electronics_noise=50,
        )
        calib = lambda x: x

    if not args["--local_tc"]:
        cell_width_guess = np.ones(1024)
    else:
        cell_width_guess = pd.read_csv(args["--local_tc"])["cell_width_mean"].values

    tc = calc_qr_tc(
        event_generator, 
        calib, 
        pixel, 
        gain, 
        cell_width_guess)

    if args["--fake"]:
        tc["cell_width_truth"] = event_generator.cell_widths / event_generator.cell_widths.mean()
     
    tc.to_csv(args["-o"], index=False)