# -*- coding: utf-8 -*-
"""
Created on Fri Nov 26 13:00:58 2025

@author: messung
"""

# libraries
import time
import os
import signal
# interface
import tkinter 
import customtkinter
# subprocess
import subprocess
import threading 
# for ssh connection with Bela
import paramiko
from pathlib import Path
# lsl
import matplotlib.pyplot as plt
from pylsl import StreamInlet, StreamInfo, resolve_stream

from nEEGlace.belaconnect import checkBelaStatus, getBelaConfig, dumpBelaConfig
from nEEGlace.connectLSL import connectstreams
# from streamEEG import plotEEG
from nEEGlace.streamPlotter import plotEEG

# from computeERP import start_erp, getTrialCount
from nEEGlace.advertiseLSL import LSLestablisher, LSLkiller




# -- SCRIPT SETUP  -------------------------------------------------------------------------------  

# enter device name  
deviceName = 'Explore_DAAH' 
# enter EEG channels in the stream 
nbchans = 32
# channel used for sound triggers
triggerChan = 1


# -- SOUND TRIGGERS PARAMS
# threshold for sound detection
soundThresh = 500


# -- OTHERS
# common outputs of push2lsl
errstr1   = 'not recognised as an internal or external command'
errstr2   = 'DeviceNotFoundError'
successtr = 'Device info packet has been received. Connection has been established. Streaming...'

# ------------------------------------------------------------------------------------------------




# project directory
project_root = Path(os.getcwd())

# set directory
os.chdir(project_root) 
ani = None

# channel index of the sound trigger 
tidx = triggerChan-1
# list of EEG chans
eegchans = list(range(nbchans))

if tidx in eegchans:
    # remove sound trigger channel from EEG channels 
    eegchans = [x for x in eegchans if x != tidx]
else:
    # adjust total channels 
    nbchans = nbchans +1

inlet, streaminfo = connectstreams()
plotEEG(inlet, eegchans, nbchans, tidx, soundThresh)