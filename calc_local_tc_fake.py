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
import matplotlib.pyplot as plt
from fake_event_gen import FakeEventGenerator as EventGenerator

args = docopt(__doc__)
print(args)
np.random.seed(0)



times = np.random.uniform(0, 1e-8, 10000).cumsum()
event_generator = EventGenerator(times)
calib = lambda x: x

pixel = int(args["--pixel"])
gain = args["--gain"]
assert gain in ["high", "low"]


all_slopes = [[] for i in range(1024)]

#fig, a = plt.subplots(1)

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

print(slope_std)
df = pd.DataFrame({
    "cell_width_mean": slope_mean / slope_mean.mean(),
    "cell_width_std": slope_std /  slope_mean.mean(),
    })


cell_width = df["cell_width_mean"].values
cell_width_std = df["cell_width_std"].values
print(cell_width_std)

fig, ax = plt.subplots(4)
plt.suptitle("Local TC evaluation with Toy MC \n 10k events - no noise - 30MHz sine")

a = ax[0]
a.errorbar(
    x=np.arange(len(cell_width)), 
    y=cell_width - cell_width.mean(), 
    yerr=cell_width_std, 
    fmt='b.',
    label="measurement")
a.plot((event_generator.cell_widths/1e-9) - 1,
    'r.',
    label="truth")

a.set_xlabel("DRS4 cells")
a.set_ylabel("individual cell deviation[ns]")
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 8+1))
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
a.plot(((event_generator.cell_widths/1e-9) - 1).cumsum(), 'r.', label="truth")
a.set_ylabel("cumulative cell delay deviation [ns]")
a.set_xlabel("DRS4 cells")
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 8+1))
a.grid()
a.legend()

# ---------------------------------------------------
a = ax[-2]
a.hist(cell_width - cell_width.mean() - ((event_generator.cell_widths/1e-9) - 1), 
    bins=100,
    histtype="step",
    label="residuals",
    )

a.set_xlabel("cell width residuals [ns]")
a.grid()
a.legend()

# ---------------------------------------------------


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