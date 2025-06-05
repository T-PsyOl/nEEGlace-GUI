# -*- coding: utf-8 -*-
"""
Created on Thu Jun  5 09:48:57 2025

@author: messung
"""


import tkinter as tk
from customtkinter import CTk, CTkButton
from multiprocessing import Process
import sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QCheckBox, QSpacerItem, QSizePolicy
import pylsl
from nEEGlace.computeERP import process_data, initialize_erp_params, plotERP, butter_bandpass, applyBPfilter
import threading

# creating the app window
class PlotWindow(QMainWindow): 
    def __init__(self):
        super().__init__()
        # main PyQt window settings 
        self.setWindowTitle("nEEGLace EEG Stream")
        self.setGeometry(100, 100, 1200, 800) 
        self.setStyleSheet("background-color: #2a2a2a; color: white;")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # main window layout (splt vertically)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # EEG signal plot title (left)
        self.eeg_header_layout = QHBoxLayout()        
        self.top_label = QLabel("EEG Signals")
        self.top_label.setStyleSheet("font-size: 15px; color: #979797;")
        self.eeg_header_layout.addWidget(self.top_label)
        # spacer
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.eeg_header_layout.addItem(spacer)
        
        # apply filter checkbox (right)
        self.filter_checkbox = QCheckBox("Apply Filter")
        self.filter_checkbox.setStyleSheet("color: lightskyblue; font-size: 15px;")
        self.filter_checkbox.setChecked(False)
        self.filter_checkbox.stateChanged.connect(self.on_filter_toggle)
        self.eeg_header_layout.addWidget(self.filter_checkbox)
        # add the header layout to the main layout
        self.main_layout.addLayout(self.eeg_header_layout)
        
        # EEG signal plot
        self.plot_top = pg.PlotWidget()
        self.plot_top.setStyleSheet("border: 2px solid #303030; border-radius: 1px;")
        self.main_layout.addWidget(self.plot_top)

        
        # bottom window layout (splt horizontally)
        self.bottom_layout = QHBoxLayout()
        
        # sound stream plot
        self.bottom_left_layout = QVBoxLayout()
        self.bottom_left_label = QLabel("Sound Stream")
        self.bottom_left_label.setStyleSheet("font-size: 15px; color: #979797;")
        self.plot_bottom_left = pg.PlotWidget()
        self.plot_bottom_left.setStyleSheet("border: 2px solid #303030; border-radius: 1px;")
        self.bottom_left_layout.addWidget(self.bottom_left_label)
        self.bottom_left_layout.addWidget(self.plot_bottom_left)
        
        # ERP plot
        self.bottom_right_layout = QVBoxLayout()
        self.bottom_right_label = QLabel("ERP Plot")
        self.bottom_right_label.setStyleSheet("font-size: 15px; color: #979797;")
        self.plot_bottom_right = pg.PlotWidget()
        self.plot_bottom_right.setStyleSheet("border: 2px solid #303030; border-radius: 1px;")
        self.bottom_right_layout.addWidget(self.bottom_right_label)
        self.bottom_right_layout.addWidget(self.plot_bottom_right)
        
        # add left and right layouts to the bottom layout
        self.bottom_layout.addLayout(self.bottom_left_layout)
        self.bottom_layout.addLayout(self.bottom_right_layout)
        # add bottom layout to the main layout
        self.main_layout.addLayout(self.bottom_layout)
        
        # auto-scaling
        self.plot_top.enableAutoRange(x= False, y=True)
        self.plot_bottom_left.enableAutoRange(x= False, y=True)
        # self.plot_bottom_right.enableAutoRange(x= True, y=True)
        
    def on_filter_toggle(self):
        if hasattr(self, "filter_callback"):
            self.filter_callback(self.filter_checkbox.isChecked())
    

# handling the data and plotting
class DataInletPlotter:
    def __init__(self, inlets, plt_main, plt_ch7, eegchans, tidx, filter_checkbox, plotPeriod=5, pullInterval=500):
        self.inlets = inlets
        self.plt_main = plt_main
        self.plt_ch7 = plt_ch7
        self.plotPeriod = plotPeriod
        self.pullInterval = pullInterval
        self.eegchans = eegchans
        self.tidx = tidx
        self.filter_checkbox = filter_checkbox
        
        # store PlotDataItems for each channel
        self.curves = []  
        # initialise PlotDataItem for each channel and add to the plot
        for inlet in self.inlets:
            for i in range(inlet.nchan):
                # create PlotDataItem
                curve = pg.PlotDataItem()
                # sound stream
                if i == self.tidx: 
                    self.plt_ch7.addItem(curve) 
                # eeg signal stream 
                elif i in self.eegchans: 
                    self.plt_main.addItem(curve)  
                self.curves.append(curve)
                
    def pullPlot(self, inlet, plotTime):
        ts, vals = inlet.pull_data()
        
        # check for valid timestamps
        if len(ts): 
            filtered_vals = vals.copy()
            if self.filter_checkbox.isChecked():
                for ichan in self.eegchans:
                    filtered_vals[:, ichan] = applyBPfilter(vals[:, ichan], lowcut=2.0, highcut=20.0, fs=250.0, order=4)
                    
                
            # compute ERP
            threading.Thread(target=process_data, args=(filtered_vals,), daemon=True).start()
            
            # plotting EEG stream
            new_ts = None
            oldOffset, newOffset = 0, 0
            for ichan in range(inlet.nchan):
                curve = self.curves[ichan]  
                # retrieve current plot data (old timestamps and values)
                old_ts, old_vals = curve.getData()
                old_ts = old_ts if old_ts is not None else np.array([])
                old_vals = old_vals if old_vals is not None else np.array([])          
                # calculate offset
                if ichan == 0:  
                    oldOffset = np.searchsorted(old_ts, plotTime)
                    newOffset = np.searchsorted(ts, plotTime)
                    new_ts = np.hstack((old_ts[oldOffset:], ts[newOffset:]))
                
                if self.filter_checkbox.isChecked() and ichan in self.eegchans:
                    data_to_plot = filtered_vals[newOffset:, ichan]
                else:
                    data_to_plot = vals[newOffset:, ichan]
                # uppend new data to the trimmed old data
                new_vals = np.hstack((old_vals[oldOffset:], data_to_plot - ichan))
                # Update the curve with new data
                curve.setData(new_ts, new_vals)
    
    def update(self):
        mintime = pylsl.local_clock() - self.plotPeriod
        for inlet in self.inlets:
            self.pullPlot(inlet, mintime)
            
    def scroll(self):
        fudgeFactor = self.pullInterval * 0.002
        plotTime = pylsl.local_clock()
        self.plt_main.setXRange(plotTime - self.plotPeriod + fudgeFactor, plotTime - fudgeFactor)
        self.plt_ch7.setXRange(plotTime - self.plotPeriod + fudgeFactor, plotTime - fudgeFactor)
        # self.plt_main.setYRange(0, 1)
        # self.plt_ch7.setYRange(-6, -5.96)
        self.plt_ch7.getAxis('left').setStyle(showValues=False)
        

def plotEEG(inlets, eegchans, nchan, tidx, trigger_thr, plotPeriod=5, updateInterval=20, pullInterval=20):
    
    app = QApplication(sys.argv)
    window = PlotWindow()
    plotter = DataInletPlotter(inlets, window.plot_top, window.plot_bottom_left, eegchans, tidx, window.filter_checkbox, plotPeriod, pullInterval)
    
    def reset_erp(use_filter):
        print(f"Filter toggled: {'ON' if use_filter else 'OFF'}")
        # reinitialize ERP parameters
        initialize_erp_params(inlets[0], srate=250, nchan=nchan,eegchans=eegchans, plot_widget=window.plot_bottom_right,trigger_thr=trigger_thr, trigger_chan=tidx)

    # assign the callback to the checkbox toggle handler
    window.filter_callback = reset_erp
    
    # initialize ERP parameters
    initialize_erp_params(inlets[0], srate=250, nchan=nchan, eegchans= eegchans, plot_widget=window.plot_bottom_right, trigger_thr= trigger_thr, trigger_chan= tidx)
    
    timers = []
    # ERP plotting 
    erp_timer = plotERP(inlets[0], srate=250, nchan=nchan, plot_widget=window.plot_bottom_right, trigger_thr= trigger_thr, eegchans= eegchans, trigger_chan= tidx)
    timers.append(erp_timer)
    # set up scrolling
    updateTimer = QtCore.QTimer()
    updateTimer.timeout.connect(plotter.scroll)
    updateTimer.start(updateInterval)
    timers.append(updateTimer)
    # set up data pulling
    pullTimer = QtCore.QTimer()
    pullTimer.timeout.connect(plotter.update)
    pullTimer.start(pullInterval)
    timers.append(pullTimer)
    window.show()
    app.exec_()
