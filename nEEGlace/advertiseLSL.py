import subprocess

# common outputs of push2lsl
errstr1   = 'not recognised as an internal or external command'
errstr2   = 'DeviceNotFoundError'
successtr = 'Device info packet has been received. Connection has been established. Streaming...'

proc = None


def LSLestablisher(deviceName='Explore_84D1'):
    global proc 
    streamStatus = 0
    isConnected = False
    
    try:
        proc = subprocess.Popen(['explorepy', 'push2lsl', '-n', deviceName], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, text=True, universal_newlines=True)
        # continuous monitoring output of subprocess
        for line in proc.stdout:
            print(line, end='')  
            # check if connection is made
            if successtr in line:
                streamStatus = 1
                isConnected = True
                print(f'{deviceName} LSL Stream Advertising')
                break
            # check for errors
            if errstr1 in line:
                streamStatus = 2
                break
            if errstr2 in line:
                streamStatus = 3
                break
        # terminate the process if not connected
        if not isConnected:
            proc.terminate()
            
    except Exception as e:
        streamStatus = 4
        # print(f'Error {e}')
    
    return streamStatus

def LSLkiller(deviceName='Explore_84D1'):
    global proc
    
    if proc is not None:
        try:      
            proc.terminate()
            proc = None  
            print(f'{deviceName} LSL Stream Killed')
            return True
        except Exception as e:
            print(f'Error {e}')
            return False
    else:
        print('No ongoing LSL stream')
        return False
