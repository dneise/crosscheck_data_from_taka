import numpy as np
from collections import namedtuple

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

    def __init__(self, trigger_times, pixel=0, gain="high", roi=1024):
        self.times = list(trigger_times)
        self.max_events = len(trigger_times)
        self.roi = roi
        self.pixel = pixel
        self.gain = gain
        self.event_counter = 0

        np.random.seed(0)
        self.cell_widths = np.ones(1024) * 1e-9 + np.random.uniform(-0.5e-9, 0.5e-9, 1024)
        self.cell_widths /= self.cell_widths.mean()
        self.cell_widths *= 1e-9
        self.nominal_width = self.cell_widths.mean()
        self.period = self.cell_widths.sum()

    def __len__(self):
        return self.max_events

    def sine_wave(self, times, amplitude=1500):
        omega = 30e6
        phase = np.random.uniform()
        return amplitude * np.sin(2 * np.pi * (omega * times + phase))

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


