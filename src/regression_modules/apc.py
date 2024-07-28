'''apc.py

Houses the class for regression APCs.
'''
import telnetlib
import time
import re

class APC:
    '''Class for representing an APC unit in the UEI Regression Room.
    
    This class was created for convenience purposes. Realistically you could make this class
    much more powerful, but for our purposes it will suffice.
    '''

    def __init__(self, ipaddr: str) -> None:
        pattern = re.compile(r'\d+\.\d+\.\d+\.\d+')
        if not pattern.match(ipaddr):
            raise ValueError('ipv4 address not configured correctly, please rewrite')
        
        for val in ipaddr.split('.'):
            if int(val) > 255 or int(val) < 0:
                raise ValueError('ipv4 address values must be between [0, 255]')
        
        self.ip = ipaddr
        self.host_num = int(ipaddr.split('.')[-1])
        self.network = '.'.join(ipaddr.split('.')[0:3])


    def set_state(self, state: str, dcpsu: bool=False, timeout: int=5):
        '''Sets the APC associated with the given ipv4 address to a given state.

        NOTE: Each of the outlets represents a different power outlet on the APC. This
            Number can vary, which is why we first get the number of outlets before
            determining which ones to power on/off.

            It is standard to have the last outlet of any APC be reserved for powering
            an Agilent unit. This is why we only refer to the last outlet whenever
            the DCPSU flag == True
        
        Args:
            state (str):        The state to set the APC to. Either "on" or "off"
            dcpsu (boolean):    Boolean flag to determine how the APC is set
                                If dcpsu = False, then we set the IOM outlets
                                If dcpsu = True, then we set the Agilent outlets
            timeout (int):      Number of seconds before the command times out
        Returns:
            None
        '''
        assert state.lower() == 'on' or state.lower() == 'off'

        # we communicate with the APCs via a telnet connection
        tn = telnetlib.Telnet()

        tn.open(self.ip, timeout=30)
        time.sleep(2)

        stdout = tn.read_until(b'User Name').decode('ascii')
        tn.write('apc'.encode('ascii') + b"\r\n")
        time.sleep(2)

        stdout = stdout + tn.read_until(b'Password').decode('ascii')
        tn.write('apc -c'.encode('ascii') + b"\r\n")
        time.sleep(2)

        stdout = stdout + tn.read_until(b'APC>', timeout=timeout).decode('ascii')

        if 'denied' in stdout:
            tn.close()
            raise ConnectionRefusedError('Error in connecting to APC {}: Access Denied'.format())

        # using regex to derive the number of outlets
        # this is useful because we can then assume the last one powers an Agilent, and we don't need
        # to know ahead of time if the APC given has 8 or 16 outlets
        for line in stdout.splitlines():
            if re.match(r"Outlets: [-+]?\d+$", line):
                num_outlets = int(line.split(' ')[-1])

        outlets = [str(num_outlets)] if dcpsu else [str(i) for i in range(1, num_outlets)]

        # formatting the command to send to the APC
        # the reason for sending 2 separate commands wasn't documented in the old low level regression
        # code, so for safety's sake it was kept
        if len(outlets) > 8:
            command1 = state + ' ' + ' '.join(outlets[:8]) + '\r\n'
            command2 = state + ' ' + ' '.join(outlets[8:]) + '\r\n'
        else:
            command1 = state + ' ' + ' '.join(outlets) + '\r\n'
            command2 = None

        commands = [command1, command2]

        # writing the commands to the APC
        for c in commands:
            if not c:
                continue
            tn.write(str(c).encode())
            cmd_out = tn.read_until(b'APC>', timeout=timeout)
            
            if 'OK\r\n' not in cmd_out.decode():
                raise Exception('Command Unsuccessful')

        tn.write(b'exit\r\n')
        tn.close()    


    def power_cycle(self, dcpsu=False, sleep_time: int=10):
        '''Power-cycles the APC associated with the given APC number.
        
        Args:
            dcpsu (boolean):    Boolean flag to determine how the APC is set
                                If dcpsu = False, then we set the IOM outlets
                                If dcpsu = True, then we set the Agilent outlets
            sleep_time (int):   Number of sleep between set_state calls
        Returns:`
            None
        '''
        self.set_state('off', dcpsu)
        time.sleep(sleep_time)
        self.set_state('on', dcpsu)
        time.sleep(sleep_time)


    def __str__(self) -> str:
        return 'APC ' + str(self.ip)

    def __repr__(self) -> str:
        return str(self.host_num)


### ============================================================================================
### The functions below allow for users to have a more "scripting" approach to interacting with
### the hardware. While they are no longer used in low level regression, they have been kept
### for convenience purposes.
### ============================================================================================
def set_state(state: str, apc_ip: str, dcpsu: bool=False, timeout: int=5):
    '''Sets the APC associated with the given ipv4 address to a given state.

    NOTE: Each of the outlets represents a different power outlet on the APC. This
          Number can vary, which is why we first get the number of outlets before
          determining which ones to power on/off.

          It is standard to have the last outlet of any APC be reserved for powering
          an Agilent unit. This is why we only refer to the last outlet whenever
          the DCPSU flag == True
    
    Args:
        state (str):        The state to set the APC to. Either "on" or "off"
        apc_ip (str):       The ipv4 address of the APC to send the command to
        dcpsu (boolean):    Boolean flag to determine how the APC is powered off
                            If dcpsu = False, then we cycle the IOMs
                            If dcpsu = True, then we cycle the Agilents
        timeout (int):      Number of seconds before the command times out
    Returns:
        None
    '''
    assert state.lower() == 'on' or state.lower() == 'off'

    # we communicate with the APCs via a telnet connection
    tn = telnetlib.Telnet()

    tn.open(apc_ip, timeout=30)
    time.sleep(2)

    stdout = tn.read_until(b'User Name').decode('ascii')
    tn.write('apc'.encode('ascii') + b"\r\n")
    time.sleep(2)

    stdout = stdout + tn.read_until(b'Password').decode('ascii')
    tn.write('apc -c'.encode('ascii') + b"\r\n")
    time.sleep(2)

    stdout = stdout + tn.read_until(b'APC>', timeout=timeout).decode('ascii')

    if 'denied' in stdout:
        tn.close()
        raise ConnectionRefusedError('Error in connecting to APC {}: Access Denied'.format())

    # using regex to derive the number of outlets
    # this is useful because we can then assume the last one powers an Agilent, and we don't need
    # to know ahead of time if the APC given has 8 or 16 outlets
    for line in stdout.splitlines():
        if re.match(r"Outlets: [-+]?\d+$", line):
            num_outlets = int(line.split(' ')[-1])

    outlets = [str(num_outlets)] if dcpsu else [str(i) for i in range(1, num_outlets)]

    # formatting the command to send to the APC
    # the reason for sending 2 separate commands wasn't documented in the old low level regression
    # code, so for safety's sake it was kept
    if len(outlets) > 8:
        command1 = state + ' ' + ' '.join(outlets[:8]) + '\r\n'
        command2 = state + ' ' + ' '.join(outlets[8:]) + '\r\n'
    else:
        command1 = state + ' ' + ' '.join(outlets) + '\r\n'
        command2 = None

    commands = [command1, command2]

    # writing the commands to the APC
    for c in commands:
        if not c:
            continue
        tn.write(str(c).encode())
        cmd_out = tn.read_until(b'APC>', timeout=timeout)
        
        if 'OK\r\n' not in cmd_out.decode():
            raise Exception('Command Unsuccessful')

    tn.write(b'exit\r\n')
    tn.close()    



def power_cycle(apc_ip: str, sleep_time: int=10, dcpsu=False):
    '''Power-cycles the APC associated with the given APC number.
    
    Args:
        apc_ip (str):       The ipv4 address of the APC to power cycle
        dcpsu (boolean):    Boolean flag to determine how the APC is powered off
                            If dcpsu = False, then we cycle the IOMs
                            If dcpsu = True, then we cycle the dongles
    Returns:
        None
    '''
    set_state('off', apc_ip, dcpsu)
    time.sleep(sleep_time)
    set_state('on', apc_ip, dcpsu)
    time.sleep(sleep_time)