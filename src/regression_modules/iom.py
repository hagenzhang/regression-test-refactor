'''ioms.py

Houses the class for regression IOMs.
'''
import os
import time
import subprocess
import re

class IOM:
    '''Class for representing an IOM unit in the UEI Regression Room'''

    # These key values help communicate what CPU model this IOM supposedly has
    KEY_5200 = '5200'
    KEY_8347_1 = '8347_1'
    KEY_8347_2 = '8347_2'
    KEY_8347_3 = '8347_3'
    KEY_SOLOX = 'SOLOX'
    KEY_ZYNC = 'ZYNC'
    ALL_KEYS = [KEY_5200, KEY_8347_1, KEY_8347_2, KEY_8347_3, KEY_SOLOX, KEY_ZYNC]


    def __init__(self, ipaddr: str, cpu: str) -> None:
        # cpu model validation:
        if cpu not in self.ALL_KEYS:
            raise ValueError('Invalid CPU type: {}'.format(cpu))
        
        # ipv4 address validation
        pattern = re.compile(r'\d+\.\d+\.\d+\.\d+')
        if not pattern.match(ipaddr):
            raise ValueError('ipv4 address not configured correctly, please rewrite')
        
        for val in ipaddr.split('.'):
            if int(val) > 255 or int(val) < 0:
                raise ValueError('ipv4 address values must be between [0, 255]')
        
        # assigning values
        self.cpu = cpu
        self.ip = ipaddr
        self.host_num = int(ipaddr.split('.')[-1])
        self.network = '.'.join(ipaddr.split('.')[0:3])


    def ping(self, attempts: int = 1, pause: int = 1):
        '''Attempts to reach the IOM via pings a given number of times.
    
        This function will attempt to reach the given IOM a specified number of times. 
        If it is unable to reach it, then this function will return False. If it was 
        successful in reaching the IOM, then it will return True.
        
        Between each attempt it will also pause for the given number of seconds.
        
        Args:
            attempts (int): the number of attempts to reach to IOM via ping.
            pause (int):    the number of seconds to pause between each ping.
        Returns:
            reachable (bool):   True if the IOM is reachable, else False.
            num_tries (int):    the number of tries it took to reach the IOM.
        '''
        for i in range(1, attempts + 1):
            result = subprocess.call("ping -w 2000 " + self.ip, stdout=subprocess.DEVNULL)
            time.sleep(pause)
            if result == 0:
                return True, i
            
        # if we reach here, we failed to ping
        return False, attempts


    def update_firmware_pdna(
        self,
        firmware_path: str,
        load_exe_path: str,
        attempts: int = 1
    ):
        '''Updates the PowerDNA firmware in this IOM via the LoadFW.exe app.

        This function assumes that the IOM is also set to PDNA mode, NOT UEIPAC.

        The source code for the LoadFW.exe app is located in subversion, under 
        ~/Software/PowerDNA/3.3.x/PDNA_Utilities/LoadFW.

        Args:
            firmware_path (str):    filepath to the firmware file to use.
            load_exe_path (str):    filepath to a usable LoadFW executable.
            is_pac (bool):          True if we are running in PAC mode, else False.
            attempts (int):         number of firmware update attempts before giving up.
        Returns:
            success (bool):     True if the firmware updated successfully.
            attempts (int):     number of attempts it took to succeed / fail.
        '''
        for i in range(1, attempts + 1):
            # this command format is what works with the LoadFW code written in subversion. Ideally this will never change.
            load_command =  [load_exe_path, '--ip', self.ip, 
                                            '--filename', firmware_path, 
                                            '--no-force', '--max-reset', '60', '--verbosity', '0']
            
            proc = subprocess.run(load_command, stdout=subprocess.DEVNULL)
            
            if proc.returncode == 0:
                return True, i

        # if we reach here, we failed to update
        return False, attempts
    

    def update_firmware_pac(self):
        '''Not Implemented, Refer to Hagen Zhang's Co-op folder for more information'''
        raise NotImplementedError('UEIPAC mode firmware updates are not supported yet!')
    

    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and value.ip == self.ip
            
    def __hash__(self):
        return hash(self.ip)

    def __str__(self) -> str:
        return 'IOM ' + str(self.ip)

    def __repr__(self) -> str:
        return str(self.host_num)



### ============================================================================================
### The functions below allow for users to have a more "scripting" approach to interacting with
### the hardware. While they are no longer used in low level regression, they have been kept
### for convenience purposes.
### ============================================================================================
def ping_iom(iom_ip: str, attempts: int = 1):
    '''Pings the IOM at the given IP address.
    
    This function will attempt to reach the given IOM a specified number of times. 
    If it is unable to reach it, then this function will return False. If it was 
    successful in reaching the IOM, then it will return True.
    
    This function contains a 1 second sleep between each ping and a 3 seconds timeout.
    NOTE: maybe these could be made into a variable number, depending on the expected rtt?
    
    Args:
        iom_ip (str):       the ipv4 address of the IOM the function should ping.
    Returns:
        reachable (bool):   True if the IOM is reachable, else False.
        num_tries (int):    the number of tries it took to reach the IOM.
    '''
    DEVNULL = open(os.devnull, 'w')

    for i in range(1, attempts + 1):
        result = subprocess.call("ping -n 1 -w 3000 " + iom_ip, stdout=DEVNULL)
        time.sleep(1)
        if result == 0:
            return True, i
        
    # if we reach here, we failed to ping
    return False, attempts


def update_firmware(
    iom_ip: str,
    firmware_path: str,
    load_exe_path: str,
    is_pac: bool,
    attempts: int = 1
):
    '''Updates the firmware in an IOM via the LoadFW.exe app.

    The source code for the LoadFW.exe app is located in subversion, under 
    ~/Software/PowerDNA/3.3.x/PDNA_Utilities/LoadFW.

    As of 06/2024, LoadFW does not support firmware updates for PAC mode.

    Args:
        iom_ip (str):           ipv4 address of the IOM we want to update.
        firmware_path (str):    filepath to the firmware file to use.
        load_exe_path (str):    filepath to a usable LoadFW executable.
        is_pac (bool):          True if we are running in PAC mode, else False.
        attempts (int):         number of firmware update attempts before giving up.
    Returns:
        returncode (int):   return code from running LoadFW.exe.
        attempts (int):     number of attempts it took to succeed / quit.
    '''
    
    if is_pac:
        raise NotImplementedError('PAC support for firmware updates has not been implemented yet')

    for i in range(1, attempts + 1):
        # this command format is what works with the LoadFW code written in subversion. Ideally this will never change.
        load_command =  [load_exe_path, '--ip', iom_ip, '--filename', firmware_path, '--no-force', '--max-reset', '60', '--verbosity', '0']
        proc = subprocess.run(load_command, stdout=subprocess.DEVNULL)

        # on success, make sure to break the loop
        if proc.returncode == 0:
            return proc.returncode, i

    # if we reach here, we failed to update
    return proc.returncode, attempts


    
    