'''agi.py

Houses the class for regression Agilents.
'''
import pyvisa
import time
import re

class Agilent:
    '''Class for representing an Agilent unit in the UEI Regression Room.
    
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


    def set_state(self, state: str, voltage: float=0, current: float=0):
        '''Sets the Agilent associated with the given ipv4 address to a given state.
        
        If the state is 'off', then we ignore the voltage and current values completely.
        If the state is 'on', we will use the voltage and current values.
        
        Args:
            state (str):        state to set the Agilent to, either 'on' or 'off'.
            agi_ip (str):       ipv4 address of the Agilent unit.
            voltage (float):    the voltage setting for the Agilent.
            current (float):    the current setting for the the Agilent.
        Returns:
            None
        '''
        assert state.lower() == 'on' or state.lower() == 'off'
        
        resource_name = 'TCPIP0::' + self.ip + '::INSTR'
        
        # create the PYVisa resource manager object and open the connection to the power supply
        rm = pyvisa.ResourceManager()
        instrument = rm.open_resource(resource_name)

        # query the device and make sure the device is a power supply
        # NOTE: should we be doing this for setting the APC state too?
        idn = instrument.query('*idn?') # type: ignore
        if idn.find('Agilent') <= 0 and idn.find('N57') <= 0:
            return

        if state == 'on':
            # make sure voltage is between 0V and 600V (??)
            assert 0.0 <= voltage <= 600.0

            # make sure current is between 0A and 200A (??)
            assert 0.0 <= current <= 200.0
        else:
            # If off set voltage to 0 and current to 1A (??)
            voltage = 0.0
            current = 0.0 # NOTE: used to be 1.0 in the old code

        # write the voltage, current, and state to the power supply
        instrument.write('OUTP {}'.format(state.upper()))   # type: ignore
        instrument.write(':VOLT {:0.6f}'.format(voltage))   # type: ignore
        instrument.write(':CURR {:0.6f}'.format(current))   # type: ignore
        
        # close the instrument instance
        instrument.close()
        

    def power_cycle(self, voltage: float=12.0, current: float=1.0, sleep_time: int=5):
        '''Power-cycles the Agilent associated with the given Agilent ip address.

        This simply entails turning the Agilent off and on again.

        Args:
            agi_ip (str):       ipv4 address of the Agilent unit.
            voltage (float):    the voltage setting for the Agilent.
            current (float):    the current setting for the the Agilent.
            sleep_time (float): the time to sleep between turning the Agilent off/on
        Returns:
            None
        '''
        set_state('off', self.ip, voltage=0, current=0)
        time.sleep(sleep_time)
        set_state('on', self.ip, voltage=voltage, current=current)
        time.sleep(sleep_time)


    def __str__(self) -> str:
        return 'Agilent ' + str(self.ip)

    def __repr__(self) -> str:
        return str(self.host_num)


### ============================================================================================
### The functions below allow for users to have a more "scripting" approach to interacting with
### the hardware. While they are no longer used in low level regression, they have been kept
### for convenience purposes.
### ============================================================================================

def set_state(state: str, agi_ip: str, voltage: float=0, current: float=0):
    '''Sets the Agilent associated with the given ipv4 address to a given state.
    
    If the state is 'off', then we ignore the voltage and current values completely.
    If the state is 'on', we will use the voltage and current values.
    
    Args:
        state (str):        state to set the Agilent to, either 'on' or 'off'.
        agi_ip (str):       ipv4 address of the Agilent unit.
        voltage (float):    the voltage setting for the Agilent.
        current (float):    the current setting for the the Agilent.
    Returns:
        None
    '''
    assert state.lower() == 'on' or state.lower() == 'off'
    
    resource_name = 'TCPIP0::' + agi_ip + '::INSTR'
    
    # create the PYVisa resource manager object and open the connection to the power supply
    rm = pyvisa.ResourceManager()
    instrument = rm.open_resource(resource_name)

    # query the device and make sure the device is a power supply
    # NOTE: should we be doing this for setting the APC state too?
    idn = instrument.query('*idn?') # type: ignore
    if idn.find('Agilent') <= 0 and idn.find('N57') <= 0:
        return

    if state == 'on':
        # make sure voltage is between 0V and 600V (??)
        assert 0.0 <= voltage <= 600.0

        # make sure current is between 0A and 200A (??)
        assert 0.0 <= current <= 200.0
    else:
        # If off set voltage to 0 and current to 1A (??)
        voltage = 0.0
        current = 0.0 # NOTE: used to be 1.0 in the old code

    # write the voltage, current, and state to the power supply
    instrument.write('OUTP {}'.format(state.upper()))   # type: ignore
    instrument.write(':VOLT {:0.6f}'.format(voltage))   # type: ignore
    instrument.write(':CURR {:0.6f}'.format(current))   # type: ignore
    
    # close the instrument instance
    instrument.close()
    

def power_cycle(agi_ip: str, voltage: float=12.0, current: float=1.0, sleep_time: int=5):
    '''Power-cycles the Agilent associated with the given Agilent ip address.

    This simply entails turning the Agilent off and on again.

    
    Args:
        agi_ip (str):       ipv4 address of the Agilent unit.
        voltage (float):    the voltage setting for the Agilent.
        current (float):    the current setting for the the Agilent.
        sleep_time (float): the time to sleep between turning the Agilent off/on
    Returns:
        None
    '''
    set_state('off', agi_ip, voltage=0, current=0)
    time.sleep(sleep_time)
    set_state('on', agi_ip, voltage=voltage, current=current)
    time.sleep(sleep_time)

