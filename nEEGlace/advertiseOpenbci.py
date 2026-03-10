import time
import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from pylsl import StreamInfo, StreamOutlet
import threading

board = None

def LSLestablisherOBC(serial_port='COM3'): 
    global board, outlet
    
    try:
        params = BrainFlowInputParams()
        params.serial_port = serial_port
        
        board = BoardShim(BoardIds.CYTON_BOARD.value, params)
        board.prepare_session()
        board.start_stream()
        
        sampling_rate = BoardShim.get_sampling_rate(BoardIds.CYTON_BOARD.value)
        eeg_channels = BoardShim.get_eeg_channels(BoardIds.CYTON_BOARD.value)
        
        info = StreamInfo('OpenBCI_Cyton', 'ExG', len(eeg_channels), sampling_rate, 'float32', 'cyton1234')
        outlet = StreamOutlet(info)
        
        # start streaming in a separate daemon thread
        def push_data():
            while board is not None:
                data = board.get_current_board_data(32)
                if data.shape[1] > 0:
                    eeg_data = data[eeg_channels, :].T
                    for sample in eeg_data:
                        outlet.push_sample(sample.tolist())
                time.sleep(0.01)  

        t = threading.Thread(target=push_data, daemon=True)
        t.start()

        print("Cyton connected. Streaming to LSL...")
        return 1
        

    except Exception as e:
        print(f"Error: {e}")
        return 2

    


def LSLkillerOBC():
    global board
    
    if board is not None:
        board.stop_stream()
        board.release_session()
        board = None
        outlet = None
        print("Cyton LSL Stream Killed")
        return True
    else:
        print("No ongoing LSL stream")
        return False