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
N_trials = int(100000/3)

def pulse(x, x0=0, sigma=1, A=1):
    y = np.exp(-1/2*((x-x0)/sigma)**2)
    return y

cell_width = np.ones(N_cells) + np.random.normal(0, cell_width_variation, size=N_cells)
cell_width /= cell_width.mean() / nominal_cell_width  # make sure the average cell width == nominal_cell_width

cell_width_B = (cell_width + np.roll(cell_width, -1)) / 2

dual_cell_width = np.concatenate((cell_width, cell_width))
sample_times = dual_cell_width.cumsum() - dual_cell_width[0]  # from 0 to 2 x period


max_cell = []
results = []
plt.ion()
plt.figure()
for j in range(100):
    trigger_times = np.random.uniform(0, period, N_trials)
    for trigger_time in tqdm(trigger_times):

        stop_cell = np.searchsorted(sample_times, trigger_time)
        event_sample_times = sample_times[stop_cell:stop_cell + N_cells]

        pulse_time = trigger_time + period/2
        p = pulse(event_sample_times, x0=pulse_time, sigma=pulse_width, A=pulse_height)
        X = p.argmax()
        Xmod = (X + stop_cell) % N_cells
        max_cell.append(Xmod)
    

    h, _ = np.histogram(np.array(max_cell), bins=np.arange(N_cells+1)-0.5)
    h = h.astype('f8')
    h /= h.mean() / nominal_cell_width

    #h -= cell_width_B

    residuals = np.sqrt(((h - cell_width_B)**2).sum()) / nominal_cell_width
    results.append((len(max_cell)/N_cells, residuals))

    RR = np.array(results).T

    plt.clf()
    plt.plot(RR[0], RR[1], '.:' )
    plt.grid()
    plt.ylabel("RMS [nominal cell width]")
    plt.xlabel("events per DRS4 cell")
    plt.pause(0.01)

plt.ioff()
plt.show()