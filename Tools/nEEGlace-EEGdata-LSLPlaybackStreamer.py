# -*- coding: utf-8 -*-
"""
Created on Fri Nov 26 12:35:12 2025

The script streams via LSL the EEG data recorded with nEEGlace. This code can be 
used for testing the nEEGlace GUI stream and ERP functionalities. 

@author: Abin Jacob
         Carl von Ossietzky University Oldenburg
         abin.jacob@uni-oldenburg.de
"""

# libraries 
import mne
import time
import os
from pathlib import Path
from pylsl import StreamInfo, StreamOutlet, local_clock


# project directory
project_root = Path(os.getcwd())
# EEGLab file to load (.set)
filename = 'SUB05_Oddball_Int.set'
filepath = os.path.join(project_root,'Tools', 'Data', filename)
# load file in mne 
raw = mne.io.read_raw_eeglab(filepath, eog= 'auto', preload= True)

# extract data and times
data, times = raw[:, :]
data *= 1e6   
# sampling frequency 
sfreq = raw.info['sfreq']
# channel names 
chnames = raw.info['ch_names']
nchans = len(chnames)

# create EEG StreamInfo 
eeg_info = StreamInfo('nEEGlacestream', 'ExG', nchans, sfreq, 'float32', 'myuid4242')

# Add channel information
channels = eeg_info.desc().append_child("channels")
for ch_name in chnames:
    channels.append_child("channel")\
             .append_child_value("name", ch_name)\
             .append_child_value("unit", "microvolts")\
             .append_child_value("type", "EEG")

# Initialize the StreamOutlet
eeg_outlet = StreamOutlet(eeg_info)
print("Now streaming nEEGlace EEG data...")

# stream the data and markers
for i in range(data.shape[1]):
    # stream EEG sample
    sample = data[:, i].tolist()
    eeg_outlet.push_sample(sample, local_clock())    
    # wait before sending the next sample to mimic real-time streaming
    time.sleep(1.0 / sfreq)


