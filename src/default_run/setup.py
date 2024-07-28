'''setup.py

Contains the master function that controls the Low Level Regression setup process
'''
import os
import time
from datetime import datetime

import regression_logger.log as log
import regression_constants as constants
import run_helpers.setup_h as setup_util
import run_helpers.power as power


def run_setup(
    config: dict,
    master_out_path: str = constants.MASTER_OUTPUT_PATH,
    temp_dir_path: str = constants.TEMP_DIRECTORY_PATH
):
    '''Runs the setup process for the Regression Tests

    On default runs, this function will complete the following:
    1) Create a config dictionary based on the run arguments
    2) Do some basic folder validation & creation (like making sure a run results folder exists)
    3) Power on the regression room hardware
    4) Ensure all IOMs are running on the desired mode (by default PDNA, not PAC)
    5) Update the firmware to match the build version specified for the run
    6) Power cycle all of the hardware
    
    Args:
        args (argsparse.Namespace): parsed command line arguments.
        master_out_path (str):      filepath to the Low Level Regression master output directory.
        run_out_path (str):         filepath to the directory where all of the run result directories will be stored.
        temp_dir_path (str):        filepath for a temp directory.
    Returns:
        config (dict):              configuration dictionary to determine the run's behavior.
    '''
    ###############################################################################################
    # Before anything else, we need to get the logs and run directory working. We do this to make
    # sure that even if the run dies in the middle, the logs will still be in the appropriate spot.
    # There are some steps we need to take in order to make that happen, like directory creation
    # and some naming.

    now = datetime.now() # we base the name of the run on the time it was started
    day_format = r'%Y_%m_%d'
    time_format = r'%H.%M.%S'
    run_time = '{}-{}'.format(now.strftime(day_format), now.strftime(time_format))
    
    run_directory = os.path.join(master_out_path, '{}_results'.format(run_time))
    run_logs = os.path.join(run_directory, '{}_run.log'.format(run_time))

    # Create a new high-level results folder if one does not exist
    if not os.path.exists(master_out_path):
        os.mkdir(master_out_path)
    os.mkdir(run_directory)

    log.init_logs(run_logs) # loads the log config to use
    ###############################################################################################

    log.LOG_HEADER.info("==============================================")
    log.LOG_HEADER.info("======== Running Low-Level Regression ========")
    log.LOG_HEADER.info("==============================================\n")
    log.LOG_HEADER.info('======== Running Setup Process ========')

    ### Config Creation: 
    # This dictionary will now determine a lot of the run's behavior. Mutate with extreme caution!
    log.LOG_LVL_1.info('Building configuration dictionary...')
    setup_util.build_config_dict(config, run_directory)

    ### Static Tag Additions:
    # We add in some of the tags we know won't change throughout the run.
    config['tags'] = config['tags'] + constants.VM_TAG(config['vms'])
    if config['nopower']:
        config['tags'] = config['tags'] + constants.NO_HARDWARE_TAG
    if config['nofirmwareupdate']:
        config['tags'] = config['tags'] + constants.NO_FIRMWARE_TAG
    if config['pac']:
        config['tags'] = config['tags'] + constants.PAC_TAG
    if config['sslport']:
        config['tags'] = config['tags'] + constants.ENCRYPTED_TAG

    ### Hardware Conversion:
    # We pass in which IOMs/APCs/Agilents we want to run on via a list of device numbers. Now, we need
    # to convert those numbers into a list of IOM/APC/Agilent objects.
    log.LOG_LVL_1.info('Converting hardware numbers to python hardware classes...')
    ioms, apcs, agis = power.device_nums_to_device_objs(config['active_ioms'], config['active_apcs'], config['active_agis'])
    log.LOG_LVL_2.debug('IOMS: {}'.format(ioms))
    log.LOG_LVL_2.debug('APCS: {}'.format(apcs))
    log.LOG_LVL_2.debug('AGIS: {}'.format(agis))
    
    # Now, we override the config values, and store the hardware objects instead of just numbers.
    config['active_ioms'] = ioms
    config['active_apcs'] = apcs
    config['active_agis'] = agis
    
    ### Filepath Validation
    # running some filepath validation to make sure all the necessary dirs are created
    log.LOG_LVL_1.info('Running filepath validation...')
    setup_util.filepath_validation(config, temp_dir_path)

    ### Power Processes
    # power-cycling, updating firmware, and pinging the IOMs to ensure functionality
    # non-responsive IOMs are ignored for the rest of the run
    if not config['nopower']:
        try:
            log.LOG_LVL_1.info('Attempting to power cycle IOMs')  
            config['active_apcs'], _ = power.cycle_apcs(config['active_apcs'])
            
            time.sleep(5)

            log.LOG_LVL_1.info('Attempting to power cycle Dongles') 
            config['active_apcs'], _ = power.cycle_apcs(config['active_apcs'], dcpsu=True, sleep_time=50)
            config['active_agis'], _ = power.cycle_agilents(config['active_agis'])

        except Exception:
            log.LOG_LVL_1.critical('An Error Occurred While Power Cycling! Hardware may be off')

        log.LOG_LVL_1.info('Pinging IOMs to determine activity...')
        config['active_ioms'], _ = power.ping_all_ioms(config['active_ioms'])

        # update the firmware in each of the IOMs
        if not config['nofirmwareupdate']:
            try:
                log.LOG_LVL_1.info('Running Firmware updates...')
                
                setup_util.update_firmware(config['active_ioms'], config['build_version'], config['build_folder'], config['pac'])
                
                config['active_apcs'], _ = power.cycle_apcs(config['active_apcs'])
                time.sleep(5)
            except:
                log.LOG_LVL_1.critical('An Error Occurred While Updating Firmware!')

            log.LOG_LVL_1.info('Pinging IOMs to determine activity...')
            config['active_ioms'], _ = power.ping_all_ioms(config['active_ioms'])

    else:
        log.LOG_LVL_1.info('Skipping Hardware Setup...')
    
    log.LOG_LVL_1.info('Config Dict:')
    for k, v in config.items():
        log.LOG_LVL_2.debug('key: {}, value: {}'.format(k, v)) 
    
    log.LOG_HEADER.info('======== Setup Completed ========\n')

    # return the config dict from the setup.
    return config




