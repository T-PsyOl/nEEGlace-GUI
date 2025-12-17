

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
import numpy as np
from scipy.signal import butter, lfilter, filtfilt
import threading
import time 

# initialize ERP parameters
def initialize_erp_params(inlet, srate, nchan, eegchans, plot_widget, epoch_duration=0.8, maxtrials=40, trigger_thr=0.03,
                          trigger_chan=7, high_pass=0.3, hp_ord=4):
    
    global nchans, eegchannels, sampling_rate, trigger_threshold, hp, hp_order, max_trials, tidx, erp_plot_widget
    global pre_samples, post_samples, epoch_samples, ring_buffer, epochs, trial_count, last_trigger_sample, global_sample_index, win1, win2
    
    nchans              = nchan
    eegchannels         = eegchans
    sampling_rate       = srate
    trigger_threshold   = trigger_thr
    hp                  = high_pass
    hp_order            = hp_ord
    max_trials          = maxtrials
    tidx                = trigger_chan
    erp_plot_widget     = plot_widget
    
    # initialisations 
    pre_samples         = int(0.2 * srate)
    post_samples        = int(0.6 * srate)
    epoch_samples       = pre_samples + post_samples
    ring_buffer         = np.zeros((epoch_samples * 5, nchans)) 
    epochs              = []
    trial_count         = 0
    last_trigger_sample = -99999
    global_sample_index = 0
    win1                = 100
    win2                = 120

# creating a filter
def butter_bandpass(lowcut, highcut, fs, order=1):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    return butter(order, [low, high], btype='band')


def applyBPfilter(data, lowcut=2.0, highcut=20.0, fs=250.0, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    padlen = 3 * max(len(a), len(b))
    
    if len(data) <= padlen:
        pad_width = padlen - len(data) + 1
        data_padded = np.pad(data, (pad_width, pad_width), mode='constant')
        filtered = filtfilt(b, a, data_padded)
        return filtered[pad_width:-pad_width]  
    else:
        return filtfilt(b, a, data)
    
def butter_highpass(cutoff, fs, order=1):
    nyq = 0.5 * fs
    high = cutoff / nyq
    return butter(order, high, btype='high')

def applyHPfilter(data, cutoff=1.0, fs=250.0, order=4):
    b, a = butter_highpass(cutoff, fs, order=order)
    padlen = 3 * max(len(a), len(b))

    if len(data) <= padlen:
        pad_width = padlen - len(data) + 1
        data_padded = np.pad(data, (pad_width, pad_width), mode='constant')
        filtered = filtfilt(b, a, data_padded)
        return filtered[pad_width:-pad_width]
    else:
        return filtfilt(b, a, data)
    
# detect trigger and process data
def process_data(sample):
    global epochs, trial_count, raw_eeg, ring_buffer, epoch_samples, global_sample_index, last_trigger_sample
    n_samples = sample.shape[0]
    ring_buffer = np.roll(ring_buffer, -n_samples, axis=0)
    ring_buffer[-n_samples:] = sample
    trigger_buffer = ring_buffer[win1:win2, tidx]
    
    for i, value in enumerate(trigger_buffer):
        global_sample_index += 1
        if value > trigger_threshold:
            if global_sample_index - last_trigger_sample < int(0.4 * sampling_rate):
                continue
            print("Trigger detected")
            last_trigger_sample = global_sample_index
            # time.sleep(0.2)
    
            # get the epoch from ring buffer
            stidx  = (win1+i) - pre_samples
            endidx = (win1+i) + post_samples
            epoch = ring_buffer[stidx:endidx, eegchannels]
            
            # baseline 
            baseline = epoch[:pre_samples, :].mean(axis=0)
            epoch -= baseline
            
            if epoch.shape[0] == pre_samples + post_samples:
                epochs.append(epoch.copy())
            break            

# update ERP plot
def update_erp_plot():
    global erp_plot_widget, epochs
    if not epochs:
        return
    # calculate average across all epochs
    average_epoch = np.mean(np.array(epochs), axis=0)  
    n_samples, n_channels = average_epoch.shape
    # define time axis
    time_axis = np.linspace(-pre_samples / sampling_rate, post_samples / sampling_rate, n_samples)
    
    #plot each channel
    erp_plot_widget.clear()
    # erp_plot_widget.setYRange(-2, 2)  
    for i in range(n_channels):
        erp_plot_widget.plot(time_axis, average_epoch[:, i],
                             pen=pg.mkPen(pg.intColor(i, hues=n_channels), width=1))

# data collection thread
def data_loop(inlet):
    while True:
        process_data(inlet)  
        QtCore.QCoreApplication.processEvents() 
        time.sleep(0.01)

# ERP processing and plotting main
def plotERP(inlet, srate, nchan, plot_widget, trigger_thr, trigger_chan, eegchans):
    
    # use a timer for plot updates (added to set same timer as main EEG streamer)
    timer = QtCore.QTimer()
    timer.timeout.connect(update_erp_plot)
    timer.setInterval(500)  
    timer.start()
    return timer

    
