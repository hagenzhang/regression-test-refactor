'''power.py

Utility functions for interacting with the hardware in the regression room. 
'''

import time
from multiprocessing import Pool

import regression_logger.log as log
import regression_constants as constants

from regression_modules.apc import APC
from regression_modules.agi import Agilent
from regression_modules.iom import IOM

### ===============================================================================================

def device_nums_to_device_objs(
    iom_nums: list,
    apc_nums: list,
    agi_nums: list,
    iom_dict: dict = constants.IOM_CPU_DICT,
    network: str = constants.IP_PREPEND
):
    '''Takes a list of device numbers and represents them as python classes.

    IOMs, APCs, and Agilents all have corresponding python objects defined in
    their respective regression_modules.py files.

    We determine the CPU type using the iom_dict passed in.

    Args:
        iom_nums (list): ioms to convert to objects, represented by device number.
        apc_nums (list): apcs to convert to objects, represented by device number.
        agi_nums (list): agis to convert to objects, represented by device number.
        iom_dict (dict): dict to determine the cpu model of each IOM.
        network (str): network for all of the hardware objects to share.
    Returns:
        ioms (list): list of IOM objects.
        apcs (list): list of APC objects.
        agis (list): list of Agilent objects.
    '''
    ioms = []
    apcs = []
    agis = []

    for devn in iom_nums:
        for key, iom_list in iom_dict.items():
            if devn in iom_list:
                ip = network + '.' + str(devn)
                ioms.append(IOM(ip, key))
    
    for devn in apc_nums:
        ip = network + '.' + str(devn)
        apcs.append(APC(ip))

    for devn in agi_nums:
        ip = network + '.' + str(devn)
        agis.append(Agilent(ip))

    return ioms, apcs, agis

### ===============================================================================================

def __ping_child(iom: IOM):
    '''Child function for iom.ping(). Used for multiprocessing.

    Pings the IOM and returns the IOM IP address along with the reached status and
    the number of attempts.

    We will attempt to ping the IOM 10 times.

    Args:
        iom_ip_address (str):   the ipv4 address of the IOM the function should ping
    Returns:
        iom_num (int):          the last octet in the ipv4 address of the IOM
        reached (boolean):      True if the IOM responded, else False
        attempts (int):         number of attempts it took to connect to the IOM
                                -1 if the connect attempts resulted in an Exception
    '''
    try:
        reached, attempts = iom.ping(attempts=10)
    except:
        reached = False
        attempts = -1
    finally:
        return iom, reached, attempts, 


def ping_all_ioms(
    ioms: list,
    num_threads: int=constants.IOM_THREADS
):
    '''Pings all of the IOMs to check for availability.

    This function utilizes multi-threading in order to speed up the pinging process.
    It also assumes that each of the IOMs share the same network, and differ only by the
    last octet of their respective ipv4 addresses. All of the IOMs should be on the network 
    000.000.000.xxx. 

    Args:
        ioms (list):        list of IOM objects to ping.
        num_threads (int):  number of threads to ping with.
    Returns:
        active_vms (list):      list of IOMs that responded to the ping.
        inactive_vms (list):    list of IOMs that didn't respond to the ping.
    '''
    log.LOG_LVL_2.info('Pinging IOMs {}'.format(ioms))

    active_ioms = []
    inactive_ioms = []

    with Pool(num_threads) as pool:
        results = pool.map(__ping_child, ioms)
        pool.close()
        pool.join()
    
    [active_ioms.append(x[0]) if x[1] else inactive_ioms.append(x[0]) for x in results]
    
    log.LOG_LVL_2.info('Active IOMS: {}'.format(active_ioms))

    if len(inactive_ioms) > 0:
        log.LOG_LVL_2.warning('Inactive IOMs: {}'.format(inactive_ioms))
    else:
        log.LOG_LVL_3.info('All IOMs were reachable')
    
    return active_ioms, inactive_ioms


### ===============================================================================================
### POWER CYCLE HELPERS ===========================================================================

def __apc_power_cycle_child(apc: APC, sleep_time: int, dcpsu: bool):
    '''Wrapper function for power-cycling an APC. Used for multiprocessing.

    Args:
        apc_ip (str):       the ipv4 address of the APC to power cycle.
        sleep_time (int):   number of seconds to sleep for after finishing.
        dcpsu (bool):       True to for cycling the Agilents, False for cycling the IOMs.
    Returns:
        device_num (int):   the device number of the APC.
        success (bool):     True if the apc successfully cycled, else False.
    '''
    try:
        apc.power_cycle(dcpsu, sleep_time)
        return apc, True
    except Exception as e:
        log.LOG_LVL_2.error('An error occurred while power-cycling APC {}: {}'.format(apc.ip, e))
        return apc, False


def __agi_power_cycle_child(agi: Agilent, sleep_time: int):
    '''Wrapper function for power-cycling an Agilent. Used for multiprocessing.

    Args:
        agi_ip (str):       the ipv4 address of the Agilent to power cycle.
        sleep_time (int):   number of seconds to sleep for after finishing.
    Returns:
        device_num (int):   the device number of the Agilent.
        success (bool):     True if the Agilent successfully cycled, else False.
    '''
    try:
        agi.power_cycle(sleep_time)
        return agi, True
    except Exception as e:
        log.LOG_LVL_2.error('An error occurred while power-cycling Agilent {}: {}'.format(agi.ip, e))
        return agi, False


def __power_cycle_child(
    thread_function, # should be a function
    thread_args: list,
    thread_count: int,
):
    '''Helper function for multithreading power cycling.

    This function will run the given function on the given args.

    This function will return 2 list: active and inactive. If the helper
    function returns a truthy value for the 2nd value after power cycling,
    it will be marked as active. Else, it will be considered inactive.
    '''
    active = []
    inactive = []

    # The Pool class represents a pool of worker processes. It serves as a simple way to multiprocess.
    # For documentation, refer to https://docs.python.org/3/library/multiprocessing.html
    with Pool(thread_count) as pool:
        results = pool.starmap(thread_function, thread_args) # type: ignore
        pool.close()
        pool.join
    
    for i in results:
        if i[1]:
            active.append(i[0])
        else:
            inactive.append(i[0])

    return active, inactive

### ===============================================================================================

def cycle_apcs(
    apcs: list,
    dcpsu: bool = False,
    thread_count: int = constants.APC_THREADS,
    sleep_time: int = 5
):
    '''Power-cycles the IOMs inside of the regression room.

    This function turns off & on each of the APCs inside of the regression room. 
    This results in multiple IOMs or Agilents being power-cycled all at once.
    
    Args:
        apcs (list):            list of APC objects to power cycle.
        dcpsu (bool):           True to for cycling the Agilents, False for cycling the IOMs.
        thread_count (int):     number of threads to power cycle APCs with.
        sleep_time (int):       number of seconds to sleep for after finishing each cycle.
    Returns:
        active_apcs (list):     list of the APCs that were successfully power cycled.
                                each APC is represented by device number.
        inactive_apcs (list):   list of the APCs that could not be power cycled.
                                each APC is represented by device number.
    '''
    log.LOG_LVL_2.info('Power-cycling APCs: {}, DCPSU = {}'.format(apcs, dcpsu))
    
    pool_param_list = [(i, sleep_time, dcpsu) for i in apcs]
    active, inactive = __power_cycle_child(__apc_power_cycle_child, pool_param_list, thread_count)

    if len(inactive) == 0:
        log.LOG_LVL_3.info('All APCs Power-Cycled Successfully')
    else:
        log.LOG_LVL_2.error('APC Power-Cycling Error Detected')
        log.LOG_LVL_3.error('Successfully cycled APCS: {}'.format(active))
        log.LOG_LVL_3.error('Unsuccessfully cycled APCS: {}'.format(inactive))

    time.sleep(20) # give ample time for hardware to fully reboot
    return active, inactive


def cycle_agilents( 
    agis: list,
    thread_count: int = constants.AGI_THREADS,
    sleep_time: int = 5
):
    '''Power-cycles the Agilents inside of the regression room.
    
    This function turns off & on each of the Agilents inside of the regression room.
    This results in multiple Dongles being power-cycled all at once.

    NOTE: This function modifies the configuration file!
    
    Args:
        agis (list):        list of Agilent objects to power cycle.
        thread_count(int):  number of threads to power cycle Agilents with.
        sleep_time (int):   number of seconds to sleep the Agilents for after finishing each cycle.
    Returns:
        active (list):  list of the Agilents that were successfully power cycled.
        inactive(list): list of the Agilents that could not be power cycled.
    '''    
    log.LOG_LVL_2.info('Power-cycling Agilents: {}'.format(agis))

    pool_param_list = [(i, sleep_time) for i in agis]
    active, inactive = __power_cycle_child(__agi_power_cycle_child, pool_param_list, thread_count)

    if len(inactive) == 0:
        log.LOG_LVL_3.info('All Agilents Power-Cycled Successfully')
    else:
        log.LOG_LVL_2.info('Agilent Power-Cycling Error Detected')
        log.LOG_LVL_3.info('Successfully cycled Agilents: {}'.format(active))
        log.LOG_LVL_3.info('Unsuccessfully cycled Agilents: {}'.format(inactive))
    
    time.sleep(20) # give ample time for hardware to fully reboot
    return active, inactive

### ===============================================================================================
### POWER OFF HELPERS =============================================================================

def __apc_power_off_child(apc: APC, dcpsu):
    '''Wrapper function for turning off an APC. Used for multiprocessing.

    Args:
        apc (APC):      the APC object to power off.
        dcpsu (bool):   True to for controlling the Agilents, False for controlling the IOMs.
    Returns:
        apc (APC):      the APC object given.
        success (bool): True if the APC successfully powered off, else False.
    '''
    try:
        apc.set_state('off', dcpsu)
        return apc, True
    except Exception as e:
        log.LOG_LVL_2.error('Error at APC {}: {}'.format(apc.ip, e))
        return apc, False


def __agi_power_off_child(agi: Agilent):
    '''Wrapper function for powering off an Agilent. Used for multiprocessing.

    Args:
        agi (Agilent):      the Agilent object to power off.
    Returns:
        agi (Aiglent):  the Agilent object given.
        success (bool): True if the Agilent successfully powered off, else False.
    '''
    try:
        agi.set_state('off', voltage=0.0, current=0.0)
        return agi, True
    except Exception as e:
        log.LOG_LVL_2.error('Error at Agilent {}: {}'.format(agi.ip, e))
        return agi, False

### ===============================================================================================

def power_off_hardware(
    apcs: list,
    agis: list,
    thread_count_apc: int = constants.APC_THREADS,
    thread_count_agi: int = constants.AGI_THREADS
):
    '''Powers off all of the hardware specified in the config

    Args:
        apcs (list):            list of APC objects to power off.
        agis (list):            list of Agilent objects to power off.
        thread_count_apc (int): number of threads for APCs.
        thread_count_agi (int): number of threads for Agilents.
    Returns:
        None
    '''
    # Powering off the Agilents:
    with Pool(thread_count_agi) as pool:
        pool.map(__agi_power_off_child, agis)
        pool.close()
        pool.join()

    # Powering off the APCs (DCPSU True)
    param1 = [(a, True) for a in apcs]
    with Pool(thread_count_apc) as pool:
        pool.starmap(__apc_power_off_child, param1)
        pool.close()
        pool.join()

    # Powering off the APCs (DCPSU False)
    param2 = [(a, False) for a in apcs]
    with Pool(thread_count_apc) as pool:
        pool.starmap(__apc_power_off_child, param2)
        pool.close()
        pool.join()

### ===============================================================================================
