import paramiko
import os

# function fetch values from config file of bela board
def getBelaConfig():
    # creating SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        # fetch the private key for connection
        key_path = os.path.expanduser('C:\\Users\\messung\\.ssh\\id_rsa')
        private_key = paramiko.RSAKey.from_private_key_file(key_path)
        # connect to Bela Board
        client.connect(
            hostname='bela.local',
            username='root',
            pkey=private_key,
            timeout=5
        )
        # fetch current boot project
        stdin, stdout, stderr = client.exec_command('cd /root/Bela/projects/EnergyOnsetDetector && cat config.txt')
        # read output and error
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if error:
            raise Exception(f"Error reading config file: {error}")
        
        # read from text file 
        values = []
        # spliting based on newline
        for line in output.split('\n'):
            # split each line in to two parts to get the values
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                value = parts[1].strip()
                values.append(value)
            else:
                values.append(line)
        # set connection status to true 
        belastatus = True       
        return values, belastatus
    
    except Exception as e:
        # print(f"Error: {e}")
        return None, False
    
    # closing the client
    finally:
        client.close()


# function to check bela status
def checkBelaStatus():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        # fetch the private key for connection
        key_path = os.path.expanduser('C:\\Users\\messung\\.ssh\\id_rsa')
        private_key = paramiko.RSAKey.from_private_key_file(key_path)
        # connect to Bela Board
        client.connect(
            hostname='bela.local',
            username='root',
            pkey=private_key,
            timeout=5
        )
        # if the connection is successful, return True
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        client.close()

# function to dump values to config file of bela board
def dumpBelaConfig(values):
    # creating SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        # fetch the private key for connection
        key_path = os.path.expanduser('C:\\Users\\messung\\.ssh\\id_rsa')
        private_key = paramiko.RSAKey.from_private_key_file(key_path)
        # connect to Bela Board
        client.connect(
            hostname='bela.local',
            username='root',
            pkey=private_key,
            timeout=5
        )
        # prepare content to write
        # Prepare content to write
        content = [
            f'energyThreshold {values[1]}',
            f'inputGain {values[0]}',
            f'recordAudio {values[2]}',
            f'recordDuration {values[3]}'
        ]
        content_str = ''.join(content)
        
        # write data to the config file
        stdin, stdout, stderr = client.exec_command(f'echo -e "{content_str}" > /root/Bela/projects/EnergyOnsetDetector/config.txt')       
        # check for any errors
        error = stderr.read().decode().strip()       
        if error:
            raise Exception(f"Error writing to config file: {error}")
        
        # reboot bela after making changes
        stdin, stdout, stderr = client.exec_command('reboot')
        # capture stdout and stderr for reboot
        error = stderr.read().decode().strip()
        if error:
            raise Exception(f"Error rebooting Bela board: {error}")
        
        # return success status if everything was executed
        belawritestatus = True
        return belawritestatus
    
    except Exception as e:
        # print(f"Error: {e}")
        return False
    
    finally:
        # Always close the SSH client
        client.close()
    
    
    
    