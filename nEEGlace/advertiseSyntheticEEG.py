# -*- coding: utf-8 -*-
"""
Created on Wed Apr  8 12:07:17 2026

@author: messung
"""

import time
import numpy as np
from pylsl import StreamInfo, StreamOutlet
import threading

running = False

def LSLestablisherSynthetic(sampling_rate=250, n_channels=8, isi=5):
    global running, outlet
    
    try:
        
        # create LSL stream info
        info = StreamInfo('Synthetic_EEG', 'ExG', n_channels, sampling_rate, 'float32', 'fake1234')
        
        outlet = StreamOutlet(info)
        running = True

        # ERP template (in seconds)
        def create_erp_waveform():
            # 600 ms window
            t = np.linspace(0, 0.6, int(0.6 * sampling_rate))  

            # define ERP peaks 
            def gauss(t, mu, sigma, amp):
                return amp * np.exp(-0.5 * ((t - mu) / sigma) ** 2)

            erp = (
                gauss(t, 0.05, 0.015, 5) +    # P1
                gauss(t, 0.10, 0.02, -15) +    # N1
                gauss(t, 0.18, 0.025, 6) +    # P2
                gauss(t, 0.35, 0.05, 10)      # P3
            )

            return erp

        erp_template = create_erp_waveform()
        erp_len = len(erp_template)

        def stream():
            t_global = 0
            dt = 1.0 / sampling_rate

            # start after a delay
            next_stim_time = time.time() + 5  
            erp_active = False
            erp_idx = 0
            trigger_samples_left = 0

            while running:
                now = time.time()

                # base noise 
                eeg = np.random.normal(0, 5, n_channels)

                # trigger event
                if now >= next_stim_time:
                    erp_active = True
                    erp_idx = 0
                    # 200 ms pulse
                    trigger_samples_left = int(0.2 * sampling_rate)  
                    next_stim_time = now + isi

                trigger_value = 0

                if trigger_samples_left > 0:
                    trigger_value = 400  
                    trigger_samples_left -= 1

                if erp_active and trigger_samples_left == 0:
                    if erp_idx < erp_len:
                        # adding ERP to EEG channels with slight variation
                        for ch in range(7):
                            eeg[ch] += erp_template[erp_idx] + np.random.normal(0, 0.3) 

                        erp_idx += 1
                    else:
                        erp_active = False

                # trigger channel value
                eeg[7] = trigger_value

                outlet.push_sample(eeg.tolist())

                time.sleep(dt)
                t_global += dt

        thread = threading.Thread(target=stream, daemon=True)
        thread.start()

        print("Synthetic EEG streaming to LSL...")
        return 1

    except Exception as e:
        print(f"Error: {e}")
        return 2


def LSLkillerSynthetic():
    global running
    
    if running:
        running = False
        print("Synthetic EEG LSL Stream Killed")
        return True
    else:
        print("No ongoing LSL stream")
        return False