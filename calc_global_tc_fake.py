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
"""
import dragonboard as dr
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import time
import pandas as pd
from docopt import docopt
from fake_event_gen import EventGenerator

args = docopt(__doc__)
print(args)
np.random.seed(0)


times = np.random.uniform(0, 1e-8, 10000).cumsum()
event_generator = EventGenerator(times)
calib = lambda x: x

args = docopt(__doc__)
args["--max_iterations"] = int(args["--max_iterations"])
print(args)

pixel = int(args["--pixel"])
gain = args["--gain"]
assert gain in ["high", "low"]

f_calib = 30e6 # in Hz
unit_of_ti = 1e-9 # in seconds
nominal_period = 1 / (f_calib * unit_of_ti)

cell_width = np.ones(1024)
if args["--local_tc"]:
    cell_width = pd.read_csv(args["--local_tc"])["cell_width_mean"].values

T = cell_width.sum()

all_cell_widths = []
plt.ion()
fig, (a0, a2, a1) = plt.subplots(3, sharex=True)

iterations = 0
n0s = []

for event in tqdm(event_generator, total=args["--max_iterations"]):
    event = calib(event)
    calibrated = event.data[pixel][gain]
    stop_cell = event.header.stop_cells[pixel][gain]
    zero_crossings = np.where(np.diff(np.signbit(calibrated)))[0]

    for kind in [zero_crossings[0::2], zero_crossings[1::2]]:
        start = kind[:-1]
        end = kind[1:] + 1
        for start, end in zip(start, end):
            before_start = calibrated[start]
            after_start = calibrated[start + 1]
            m_start = after_start - before_start
            weight_start = 1 + before_start/m_start

            before_end = calibrated[end - 1]
            after_end = calibrated[end]
            m_end = after_end - before_end
            weight_end = -before_end/m_end

            N = end - start
            weights = np.zeros(1024)
            weights[(stop_cell + start + np.arange(N))%1024] = 1.
            weights[(stop_cell + start)%1024] = weight_start
            weights[(stop_cell + end - 1)%1024] = weight_end

            measured_period = (weights * cell_width).sum()
            if measured_period < nominal_period*0.7 or measured_period > nominal_period*1.3:
                continue

            n0 = nominal_period / measured_period
            n1 = (T - nominal_period) / (T - measured_period)
            n0s.append(n0)

            new_things = n0 * weights + n1 * (1-weights)

            cell_width *= new_things
            cell_width = np.clip(cell_width, 0, 2)
            cell_width /= cell_width.mean()
            new_period = (weights * cell_width).sum()
            
            iterations += 1
    if event.header.event_counter % 100 == 0 :
        plt.suptitle(
            ("start:{0}, stop:{1}, N:{2} \n"
            "nominal: {3:.1f} measured: {4:.1f} new: {5:.1f} \n"
            "new_things: {6:.1f} \n"
            "cell_width: {7:.1f} \n"
            "n0: {8:.1f} n1:{9:.1f} n0s:{10}"
            ).format(
                start, end, N,
                nominal_period, measured_period, new_period,
                new_things.sum(),
                cell_width.sum(),
                n0, n1, len(n0s)
                )
            )


        a0.clear()
        a1.clear()
        a2.clear()
        a0.plot((stop_cell+np.arange(1024))%1024, calibrated, '.-')
        a0.plot(weights*100, '.-')

        a0.axvline((stop_cell + start)%1024, color="g")
        a0.axvline((stop_cell + end)%1024, color="r")
        integral_devs = (cell_width - 1).cumsum()
        a1.plot(integral_devs, '.:', label=str(integral_devs[-1]))
        a1.legend()
        a2.plot(cell_width, '.:')
        a0.grid()
        a1.grid()
        a2.grid()
        plt.pause(0.0001)
        #input('?')


df = pd.DataFrame({
    "cell_width_mean": cell_width,
    "cell_width_std": np.zeros(len(cell_width))
    })

cell_width = df["cell_width_mean"].values
cell_width_std = df["cell_width_std"].values

fig, ax = plt.subplots(4)

a = ax[0]
a.errorbar(
    x=np.arange(len(cell_width)), 
    y=cell_width - cell_width.mean(), 
    yerr=cell_width_std, 
    fmt=',')
a.errorbar(
    x=np.arange(len(cell_width)), 
    y=(event_generator.cell_widths/1e-9) - 1, 
    yerr=0, 
    fmt='r.')

a.set_xlabel("DRS4 cells")
a.set_ylabel("individual cell delay [ns]")
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 8+1))
a.grid()

a = ax[1]
error_1 = cell_width_std.cumsum()
error_2 = cell_width_std[::-1].cumsum()[::-1]
error = np.minimum(error_1, error_2)
integral_deviation = (cell_width - cell_width.mean()).cumsum()
a.plot(integral_deviation, 'b-')
a.fill_between(
    x=np.arange(len(integral_deviation)), 
    y1=integral_deviation-error, 
    y2=integral_deviation+error,
    color="grey",
    alpha=0.5,
)
a.plot(((event_generator.cell_widths/1e-9) - 1).cumsum(), 'r.')
a.set_ylabel("cumulative cell delay deviation [ns]")
a.set_xlabel("DRS4 cells")
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 8+1))
a.grid()

a = ax[-2]
a.hist(cell_width - cell_width.mean() - ((event_generator.cell_widths/1e-9) - 1), 
    bins=100,
    histtype="step",
    label="residuals",
    )


a = ax[-1]
a.hist(cell_width - 1, 
    bins=100, 
    histtype="step", 
    label="$\mu$:{0:.1f} $\sigma$:{1:.1f}".format(cell_width.mean(), cell_width.std())
)



a.set_xlabel("individual cell delay [ns]")
a.grid()
a.legend()

plt.show()