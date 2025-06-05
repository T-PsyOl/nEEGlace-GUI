import pylsl
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from pyqtgraph.Qt import QtCore
import numpy as np
import sys
from nEEGlace.connectLSL import Inlet, DataInlet

# parameters for the plotting window
plotPeriod = 5  # time period to show (in seconds)
updateInterval = 60  # interval period between screen updates (in ms)
pullInterval = 500  # interval period of pulling new data (in ms)

def plotEEG(inlets):
    win = pg.GraphicsLayoutWidget(show=True, title="nEEGlace EEG Stream")
    win.resize(1000, 600)

    plt_main = win.addPlot(row=0, col=0, title="EEG Stream")
    plt_ch7 = win.addPlot(row=1, col=0, title="Sound Onset")

    plt_main.enableAutoRange(x=False, y=True)
    plt_ch7.enableAutoRange(x=False, y=True)

    curves = [pg.PlotCurveItem() for _ in range(len(inlets))]
    for curve in curves:
        plt_main.addItem(curve)

    def update_plots():
        mintime = pylsl.local_clock() - plotPeriod
        for i, inlet in enumerate(inlets):
            ts, data = inlet.pull_data()
            if ts.size > 0:
                new_ts = np.hstack((np.asarray(ts), np.zeros(len(ts))))
                new_vals = np.hstack((data[:, i], np.zeros(len(ts))))
                curves[i].setData(new_ts, new_vals)
        plt_main.setXRange(pylsl.local_clock() - plotPeriod, pylsl.local_clock())
        plt_ch7.setXRange(pylsl.local_clock() - plotPeriod, pylsl.local_clock())

    updateTimer = QtCore.QTimer()
    updateTimer.timeout.connect(update_plots)
    updateTimer.start(pullInterval)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
