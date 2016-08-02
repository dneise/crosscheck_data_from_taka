import matplotlib.pyplot as plt
import numpy as np
np.random.seed(0)  # toy mcs want to be repoducible
from tqdm import tqdm

pulse_width = 4
pulse_height = 1
nominal_cell_width = 1
cell_width_variation = 0.23
N_cells = 30   # number of cells of toy drs chip (does not have to 1024 to work
period = N_cells * nominal_cell_width
N_trials = 5000000

def pulse(x, x0=0, sigma=1, A=1):
    y = np.exp(-1/2*((x-x0)/sigma)**2)
    return y

cell_width = np.ones(N_cells) + np.random.normal(0, cell_width_variation, size=N_cells)
cell_width /= cell_width.mean() / nominal_cell_width  # make sure the average cell width == nominal_cell_width

dual_cell_width = np.concatenate((cell_width, cell_width))
sample_times = dual_cell_width.cumsum() - dual_cell_width[0]  # from 0 to 2 x period


trigger_times = np.random.uniform(0, period, N_trials)
max_cell = []
stop_cells = []
for trigger_time in tqdm(trigger_times):

    stop_cell = np.searchsorted(sample_times, trigger_time)
    event_sample_times = sample_times[stop_cell:stop_cell + N_cells]

    pulse_time = trigger_time + period/2
    p = pulse(event_sample_times, x0=pulse_time, sigma=pulse_width, A=pulse_height)
    max_cell.append((p.argmax() + stop_cell) % N_cells)
    stop_cells.append(stop_cell % N_cells)

max_cell = np.array(max_cell)
stop_cells = np.array(stop_cells)


h, _ = np.histogram(max_cell, bins=np.arange(N_cells+1)-0.5)
h = h.astype('f8')
h /= h.mean() / nominal_cell_width



fig, ax = plt.subplots(3)
ax[0].plot(h, drawstyle="steps-mid", label="max_cell")
ax[0].plot((cell_width + np.roll(cell_width, -1)) / 2, 
    drawstyle="steps-mid", 
    label="($cellwidth_i$ + $cellwidth_{i-1}$)/2"
)
ax[0].legend(loc="best")
ax[0].grid()
ax[0].set_xlim(0, N_cells)



ax[1].hist(stop_cells, 
    bins=np.arange(N_cells+1)-0.5, 
    histtype="step", 
    label="stop_cells")
ax[1].plot(cell_width / nominal_cell_width * N_trials / N_cells, 'o', label="cell width scaled")
ax[1].legend(loc="best")
ax[1].grid()
ax[1].set_xlim(0, N_cells)


ax[2].hist(trigger_times, 
    bins=np.linspace(0, period, 400), 
    histtype="step", 
    label="trigger_times")
ax[2].legend(loc="best")
ax[2].grid()

plt.show()