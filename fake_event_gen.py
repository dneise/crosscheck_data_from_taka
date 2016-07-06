import numpy as np
from collections import namedtuple
import pandas as pd

Event = namedtuple(
    'Event', ['header', 'roi', 'data', 'time_since_last_readout']
)

EventHeader_v5_1_05 = namedtuple('EventHeader_v5_1_05', [
    'event_counter',
    'trigger_counter',
    'timestamp',
    'stop_cells',
    'flag',
])


class FakeEventGenerator:

    def __init__(self, trigger_times, pixel=0, gain="high", roi=1024, random_phase=True, sine_frequency=30e6, electronics_noise=10, cell_width=None):
        self.times = list(trigger_times)
        self.max_events = len(trigger_times)
        self.roi = roi
        self.pixel = pixel
        self.gain = gain
        self.event_counter = 0
        self.random_phase = random_phase
        self.sine_frequency = sine_frequency
        self.electronics_noise = electronics_noise

        np.random.seed(0)

        if not cell_width is None:
            try:
                tc = pd.read_csv(cell_width)
                cw = tc.cell_width_mean.values
                cw = np.clip(cw, 0.2, 10)
                cw /= (cw.mean() / 1e-9)
                self.cell_widths = cw
            except:
                raise
                self.cell_widths = cell_width

        else:
            self.cell_widths = np.ones(1024) * 1e-9 + np.random.uniform(-0.5e-9, 0.5e-9, 1024)
        
        self.cell_widths /= (self.cell_widths.mean() / 1e-9)
        self.nominal_width = self.cell_widths.mean()
        self.period = self.cell_widths.sum()

    def __len__(self):
        return self.max_events

    def sine_wave(self, times, amplitude=1500):
        omega = self.sine_frequency
        if self.random_phase:
            phase = np.random.uniform()
        else:
            phase = 0
        
        signal = amplitude * np.sin(2 * np.pi * (omega * times + phase))
        if self.electronics_noise:
            signal += np.random.normal(0, self.electronics_noise, len(signal))
        return signal

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        if self.event_counter >= self.max_events:
            raise StopIteration

        time = self.times.pop(0)
        full_periods, part_period = divmod(time, self.period)

        sc = np.searchsorted(self.cell_widths.cumsum(), part_period)
        sc_time = self.cell_widths[:sc].sum()
        times = sc_time + full_periods * self.period + np.roll(self.cell_widths, -sc).cumsum()[:self.roi]

        event_header = EventHeader_v5_1_05(
            self.event_counter, 
            times, 
            time, 
            {self.pixel:{self.gain:sc}},
            None
        )
        data = {self.pixel: {self.gain: self.sine_wave(times)}}

        time_since_last_readout = None
        self.event_counter += 1
        return Event(event_header, self.roi, data, time_since_last_readout)

# --------------------------------------------

if __name__ == "__main__":

    import matplotlib.pyplot as plt
    plt.ion()

    times = np.random.uniform(0, 10e-9, 13).cumsum()
    event_generator = FakeEventGenerator(times)
    calib = lambda x: x

    events = list(event_generator)
    for event in events:
        plt.plot(event.data[0]["high"], '.:', label=str(event.header.timestamp))
    plt.legend()


