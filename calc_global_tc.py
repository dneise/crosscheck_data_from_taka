"""
Usage:
  calc_local_tc.py [options]

Options:
  -i PATH             path to file with sine wave, to be analysed [default: SinWithHighOffset2.dat]
  -c PATH             path to textfile with offsets ala Taka, to be subtracted [default: Ped300Hz_forSine.dat]
  -o PATH             path to outfile for the cell widths [default: global_tc.csv]
  --local_tc P        path to local_tc.csv file, which can be used as a starting point
  --max_iterations N  maximum number of iterations, after which to stop [default: 400]
"""
import dragonboard as dr
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import time
import pandas as pd
from docopt import docopt

args = docopt(__doc__)
args["--max_iterations"] = int(args["--max_iterations"])
print(args)
eg = dr.EventGenerator(args["-i"])
a = np.genfromtxt(args["-c"])

ped_h0 = a[:,0]


f_calib = 30e6 # in Hz
unit_of_ti = 1e-9 # in seconds

if args["--local_tc"]:
    ti = pd.read_csv(args["--local_tc"])["cell_width"].values
else:
    ti = np.ones(1024)

for evt in tqdm(eg, total=args["--max_iterations"]):
    d = evt.data[0]["high"]
    sc = evt.header.stop_cells[0]["high"]
    
    calibrated = d - np.roll(ped_h0, -sc)[:eg.roi]
    zero_crossings = np.where(np.diff(np.signbit(calibrated)))[0]

    # kind1 and kind2 could be up and down ... but I don't know who is who.
    kind1 = zero_crossings[0::2]
    kind2 = zero_crossings[1::2]

    k_names = ["kind1", "kind2"]

    u_cors = []
    for ki in range(2):
        k = [kind1, kind2][ki]
        k_name = k_names[ki]
        start = k[:-1]
        end = k[1:] + 1

        before_start = calibrated[k[:-1]]
        after_start = calibrated[k[:-1] + 1]
        m_start = after_start - before_start
        weight_start = 1 + before_start/m_start

        before_end = calibrated[k[1:]]
        after_end = calibrated[k[1:] + 1]
        m_end = after_end - before_end
        weight_end = -before_end/m_end


        for i in range(len(before_start)):
            s, e = start[i], end[i]

            foo = np.roll(ti, -sc)[s:e]
            if len(foo) < 33-7 or len(foo) > 33+7:
                continue
            weights = np.ones_like(foo)

            weights[0] = weight_start[i]
            weights[-1] = weight_end[i]
            
            bar = (weights * foo).sum()
            
            u_cor = 1/(bar * unit_of_ti * f_calib)
            u_cors.append(u_cor)
            # iterative correction
            rti = np.roll(ti, -sc)
            rti[s:e] *= u_cor
            ti = np.roll(rti, sc)
    

    if evt.header.event_counter == args["--max_iterations"]:
        break


ti = pd.DataFrame(ti, columns=["cell_width"])
ti.to_csv(args["-o"], index=False)
