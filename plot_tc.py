#!/usr/bin/env python
"""
Usage:
  plot_tc.py <input> [options]

Options:
  --show   open the figure and show it before saving it
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from docopt import docopt

args = docopt(__doc__)


tc = pd.read_csv(args["<input>"])
cell_width = tc.cell_width_mean.values
cell_width_std = tc.cell_width_std.values
N = tc.number_of_crossings.values

if "cell_width_truth" in tc:
    cell_width_truth = tc.cell_width_truth.values
    has_cell_width_truth = True
else:
    has_cell_width_truth = False
outfile = args["<input>"].replace(".csv", ".png")
print("{0} -> {1}".format(args["<input>"], outfile))
#---------------------------------------------------
fig, ax = plt.subplots(8 if has_cell_width_truth else 5, figsize=(7.95 * 1.5, 12.5125* 1.5))
plt.suptitle("Overview about: {}".format(args["<input>"]))

a = ax[0]
a.errorbar(
    x=np.arange(len(cell_width)), 
    y=cell_width, 
    yerr=cell_width_std, 
    fmt='b.',
    label="measurement")
if has_cell_width_truth:
    a.plot(cell_width_truth,
        'r.',
        label="truth")

a.set_xlabel("DRS4 cells")
a.set_ylabel("individual cell width[ns]")
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 16+1))
a.grid()
a.legend()
# ---------------------------------------------------

a = ax[1]
error_1 = cell_width_std.cumsum()
error_2 = cell_width_std[::-1].cumsum()[::-1]
error = np.minimum(error_1, error_2)
integral_deviation = (cell_width - cell_width.mean()).cumsum()
a.plot(integral_deviation, 'b.', label="measurement")
a.fill_between(
    x=np.arange(len(integral_deviation)), 
    y1=integral_deviation-error, 
    y2=integral_deviation+error,
    color="grey",
    alpha=0.5,
)
if has_cell_width_truth:
    a.plot((cell_width_truth - 1).cumsum(), 'r.', label="truth")
a.set_ylabel("cumulative cell delay deviation [ns]")
a.set_xlabel("DRS4 cells")
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 16+1))
a.grid()
a.legend()

# ---------------------------------------------------

a = ax[2]
a.plot(N, '-',
    drawstyle="steps-mid", 
    label="number of crossings"
)
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 16+1))
a.grid()
a.legend()

# ---------------------------------------------------

a = ax[3]
a.plot(tc.stop_cell, '-',
    drawstyle="steps-mid", 
    label="stop_cell"
)
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 16+1))
a.grid()
a.legend()

# ---------------------------------------------------
try:
    if has_cell_width_truth:
        a = ax[-4]
        a.plot(cell_width - cell_width_truth,
            'k.',
            label="cell width residuals[ns]")
        a.fill_between(
            x=np.arange(len(cell_width_std)), 
            y1=-cell_width_std, 
            y2=cell_width_std,
            color="grey",
            alpha=0.5,
        )

        a.set_xlabel("DRS4 cells")
        a.set_xlim(0, 1024)
        a.set_xticks(np.linspace(0, 1024, 16+1))
        a.grid()
        a.legend()
except:
    pass
# ---------------------------------------------------
if has_cell_width_truth:
    a = ax[-3]
    N = 15
    foo = np.correlate(np.concatenate((cell_width, cell_width[:N])), np.ones(N))
    bar = np.correlate(np.concatenate((cell_width_truth, cell_width_truth[:N])), np.ones(N))
    a.plot(foo - bar, '.', label="15 cells sum width residual")
    a.set_xlim(0, 1024)
    a.set_xticks(np.linspace(0, 1024, 16+1))
    a.grid()
    a.legend()

# ---------------------------------------------------

try:
    if has_cell_width_truth:
        a = ax[-2]
        residuals = cell_width - cell_width_truth
        a.hist(residuals,
            bins=100,
            histtype="step",
            label="cell width residuals $\mu$:{0:.2f} $\sigma$:{1:.2f}".format(residuals.mean(), residuals.std())
            )
        a.hist((foo-bar),
            bins=100,
            histtype="step",
            label="15 cells width residuals $\mu$:{0:.2f} $\sigma$:{1:.2f}".format((foo-bar).mean(), (foo-bar).std())
            )

        a.set_xlabel("cell width residuals [ns]")
        a.grid()
        a.legend()
except:
    pass
# ---------------------------------------------------

try:
    a = ax[-1]
    a.hist(cell_width, 
        bins=100, 
        histtype="step", 
        label="$\mu$:{0:.1f} $\sigma$:{1:.1f}".format(cell_width.mean(), cell_width.std())
    )
    a.set_xlabel("individual cell delay [ns]")
    a.grid()
    a.legend()
except:
    pass


#----------------------------------------------------
if args["--show"]:
    plt.show()
    print("figsize:", fig.get_size_inches())

plt.savefig(outfile)