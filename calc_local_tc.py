"""
Usage:
  calc_local_tc.py [options]

Options:
  -i PATH  path to file with sine wave, to be analysed [default: SinWithHighOffset2.dat]
  -c PATH  path to textfile with offsets ala Taka, to be subtracted [default: Ped300Hz_forSine.dat]
  -o PATH  path to outfile for the cell widths [default: local_tc.csv]
"""

# IPython log file

import dragonboard as dr
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import time

from docopt import docopt

args = docopt(__doc__)
print(args)
eg = dr.EventGenerator(args["-i"])
a = np.genfromtxt(args["-c"])
ped_h0 = a[:,0]

tis = [[] for i in range(1024)]

for e in tqdm(eg):
    d = e.data[0]["high"]
    sc = e.header.stop_cells[0]["high"]
    
    calibrated = d - np.roll(ped_h0, -sc)[:eg.roi]
    zero_crossings = np.where(np.diff(np.signbit(calibrated)))[0]
    before = calibrated[zero_crossings]
    after = calibrated[zero_crossings + 1]
    m = after - before
    lam = -before/m
    zero_crossings2 = zero_crossings + lam
    
    deltas = np.diff(zero_crossings2)

    cells = (sc + zero_crossings) % 1024
    for i, c in enumerate(cells):
        tis[c].append(np.abs(m[i]))

mtis = np.zeros(1024)
stis = np.zeros(1024)
for i,t in enumerate(tis):
    t = np.array(t)
    mtis[i] = t.mean()
    stis[i] = t.std()
    tis[i] = t

ti = mtis / mtis.mean()

import pandas as pd

ti = pd.DataFrame(ti, columns=["cell_width"])
ti.to_csv(args["-o"], index=False)
