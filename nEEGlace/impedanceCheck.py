import time
import threading
import explorepy
from explorepy.stream_processor import TOPICS

exp_device = None
imp_values = []
num_channels = 8
running = False
thread = None

def handle_imp(packet):
    global imp_values
    values = packet.get_impedances()[:num_channels]
    # imp_values = values
    imp_values = [v / 2 for v in values]

def _impedance_loop(duration):
    global running
    time.sleep(duration)
    running = False  

def get_impedance_values(device_name='Explore_DAAH', duration=5000, notch_freq=50, channels=8):
    global exp_device, num_channels, running, thread, imp_values
    imp_values = []
    num_channels = channels
    running = True

    exp_device = explorepy.Explore()
    exp_device.connect(device_name)

    exp_device.stream_processor.subscribe(callback=handle_imp, topic=TOPICS.imp)
    exp_device.stream_processor.imp_initialize(notch_freq=notch_freq)

    # Start background timer thread
    thread = threading.Thread(target=_impedance_loop, args=(duration,))
    thread.start()

def imp_running():
    return running

def get_latest_impedances():
    return imp_values

def shutdown_impedance():
    global exp_device, running
    running = False
    if exp_device:
        exp_device.stream_processor.disable_imp()
        exp_device.stream_processor.unsubscribe(callback=handle_imp, topic=TOPICS.imp)
        exp_device.disconnect()
        exp_device = None
