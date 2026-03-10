# -*- coding: utf-8 -*-
"""
Created on Tue Jul  8 13:07:57 2025

@author: messung
"""

import time
import explorepy
from explorepy.stream_processor import TOPICS
import argparse



def my_env_function(packet):
    """A function that receives env packets(temperature, light, battery) and does some operations on the data"""
    print("Received an environment packet: ", packet.battery)




def main():
    parser = argparse.ArgumentParser(description="Example code for data acquisition")
    parser.add_argument("-n", "--name", dest="name", type=str, help="Name of the device.")
    args = parser.parse_args()

    # Create an Explore object
    exp_device = explorepy.Explore()
    exp_device.connect('Explore_DAAH')


    # Subscribe your function to the stream publisher
    exp_device.stream_processor.subscribe(callback=my_env_function, topic=TOPICS.env)
    try:
        while True:
            time.sleep(.5)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()