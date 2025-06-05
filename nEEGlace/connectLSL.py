# connect_stream.py
import pylsl
import time
import numpy as np
from typing import List, Tuple
from pylsl import resolve_stream
import sys


class Inlet:
    def __init__(self, info: pylsl.StreamInfo, plotPeriod: int):
        self.inlet = pylsl.StreamInlet(info, max_buflen=plotPeriod, processing_flags=pylsl.proc_clocksync | pylsl.proc_dejitter)
        self.name = info.name()
        self.nchan = info.channel_count()

class DataInlet(Inlet):
    dtypes = [[], np.float32, np.float64, None, np.int32, np.int16, np.int8, np.int64]    

    def __init__(self, info: pylsl.StreamInfo, plotPeriod: int):
        super().__init__(info, plotPeriod)
        bufsize = (2 * int(info.nominal_srate() * plotPeriod), info.channel_count())
        self.buffer = np.empty(bufsize, dtype=self.dtypes[info.channel_format()])
    
    def pull_data(self):
        # pull data from the inlet
        samples, ts = self.inlet.pull_chunk(timeout=0.0, max_samples=256)
    
        if ts:
            # convert timestamps to numpy arrays
            ts = np.asarray(ts)
            samples = np.asarray(samples)
            # remove duplicate timestamps (if any)
            if len(ts) > 1:
                ts = np.unique(ts)
            # check if timestamps are ordered, otherwise sort them
            if not np.all(np.diff(ts) >= 0):
                sorted_indices = np.argsort(ts)
                ts = ts[sorted_indices]
                samples = samples[sorted_indices]
            return ts, samples
        else:
            # return empty arrays if no data is available
            return np.array([]), np.empty((0, self.nchan))
    
    def pullsample(self):
        # pull a single sample and its timestamp
        sample, timestamp = self.inlet.pull_sample(timeout=0.0)
        return timestamp, sample
    
    def pullchunk(self):
        # pull a single sample and its timestamp
        sample, timestamp = self.inlet.pull_chunk(max_samples=32, timeout=0.0)
        return timestamp, sample

def connectstreams(plotPeriod: int = 5) -> Tuple[List[DataInlet], pylsl.StreamInfo]:
    print("Looking for nEEGlace...")
    startTime = time.time()
    inlets: List[DataInlet] = []
    
    while True:
        if time.time() - startTime > 10:
            print('No streams found..')
            break

        streams = resolve_stream('type', 'ExG')
        
        if streams:
            for info in streams:
                if info.nominal_srate() != pylsl.IRREGULAR_RATE and info.channel_format() != pylsl.cf_string:
                    print('Connected to nEEGlace')
                    inlets.append(DataInlet(info, plotPeriod))
                    return inlets, info
                else:
                    print('nEEGlace not detected')
        else:
            print('No EEG streams found, retrying...')
        
        time.sleep(0.5)
    
    if not inlets:
        print('nEEGlace stream not detected')
    
    return inlets, None
