'''setup_h.py

Setup Helpers.

Contains the helper functions used in setup process of the regression run.
'''
import re
import os
import shutil
from copy import deepcopy

import regression_logger.log as log
import regression_constants as constants
from regression_modules.iom import IOM

from packaging import version
from multiprocessing import Pool

### ===============================================================================================
### CONFIG BUILDING HELPERS =======================================================================

def build_config_dict(
    config: dict,
    run_directory: str,
    pdna_installer_path: str = constants.PDNA_INSTALLERS_FOLDER
):
    '''Fills out a configuration dictionary.
    
    The dict object returned will be referenced multiple times throughout the run. 
    It serves as a "configuration" object, such that the values of each key will 
    determine how the run behaves. 

    For user reference, here is a list of all the keys the configuration dictionary will have. 
    More information about each of the keys can be found in the USEME
        nopower (bool)
        novmstart (bool)
        noinstall (bool)
        notest (bool)
        noshutdown (bool)
        nodb (bool)
        svnrevert (bool)
        noxmlcommit (bool)
        nofirmwareupdate (bool)
        pac (bool)
        vms (list)
        initial_ioms (list)
        active_ioms (list)
        active_apcs (list)
        active_agis (list)
        build_version (str)
        run_directory (str)
        run_vm_logs (str)
        run_vm_results (str)
        build_folder (str)
        autogen_diff_xmls (list)
        sslport (bool)
        tags (str)

    Args:
        config (dict):              the configuration dictionary of this run
        master_out_path (str):      filepath the output directory
        pdna_installer_path (str):  path to the "PowerDNA Installers" directory inside of builder2
    Returns:
        None (modifes dict in place, no need for a return)
    '''
    config['run_directory'] = run_directory
    config['run_vm_logs'] = os.path.join(run_directory, 'vm_logs')
    config['run_vm_results'] = os.path.join(run_directory, 'vm_results')

    # These values should not be initialized by the user, they are purely for tagging purposes 
    # (used to communicate with the website)
    config['initial_ioms'] = deepcopy(config['active_ioms'])
    config['autogen_diff_xmls'] = []
    config['expected_test_count'] = 0
    config['actual_test_count'] = 0
    config['tags'] = '#'

    # Sets build version and derives the build folder to use in builder2
    if not config['build_version']:
        config['build_version'], config['build_folder'] = __get_latest_build_version(pdna_installer_path)
    else:
        config['build_folder'] = __get_build_folder_from_version(config['build_version'], pdna_installer_path)
    
### ===============================================================================================

def filepath_validation(
    config: dict,
    temp_dir_path: str,
):
    '''Ensures that all the necessary directories exist for the current run.

    If a directory does not exist, it will create it automatically.

    Args:
        config (dict):          configuration dictionary to determine the run's behavior.
        master_out_path (str):  filepath to the Low Level Regression master output directory.
        temp_dir_path (str):    filepath for a temp directory.
    Returns:
        None
    '''            
    # Create a temp directory to hold temporary resources during the run.
    # All files in the temp directory will be deleted towards the end, but the directory itself won't be.
    if not os.path.exists(temp_dir_path):
        log.LOG_LVL_2.info('Creating temp directory...')
        os.mkdir(temp_dir_path)   
        log.LOG_LVL_3.info('Temp directory created at {}'.format(temp_dir_path))
    else:
        log.LOG_LVL_2.info('Temp directory found at {}'.format(temp_dir_path))
    
    # Create a folder to hold the results of this particular run
    log.LOG_LVL_2.info('Creating run result directories...')
    os.mkdir(config['run_vm_logs'])
    os.mkdir(config['run_vm_results'])
    log.LOG_LVL_3.info('Run result directory located at: {}'.format(config['run_directory']))

### ===============================================================================================
### FIRMWARE UPDATING FUNCTIONS ===================================================================

def update_firmware(
    ioms: list,
    build_ver: str,
    build_folder: str,
    pac: bool = False,
):
    '''Updates the firmware in all of the IOMs.
    
    This function is simply used to delegate functionality depending on the "mode".
    The firmware updating process should be fairly stable, and changes to this functionality 
    must be approached with caution.

    Args:
        ioms (list):        list of IOM objects to update.
        build_ver (str):    desired build version to update the IOMs to.
        build_folder (str): path to the build directory of your desired build version.
        pac (bool):         True if the IOMs are in PAC mode, else False.
    Returns:
        None
    '''
    if pac:
        update_all_pac_firmware(ioms)
    else:
        update_all_pdna_firmware(ioms, build_ver, build_folder)


def update_all_pdna_firmware(
    ioms: list,
    build_version: str,
    build_folder: str,
    load_exe_path: str = constants.LOAD_FIRMWARE_EXE,
    firmware_dir: str = constants.TEMP_DIRECTORY_PATH,
    num_threads: int = constants.IOM_THREADS
):
    '''Runs update_firmware_pdna on all of the given IOM objects.
    
    NOTE: build_version and build_folder is a bit of a redundancy. Since build_folder is only
    ever really used for firmware updates, you could not store it in the configuration dict and
    only use it here.

    Args:
        ioms (list):            list of IOM objects to update.
        build_ver (str):        desired build version to update the IOMs to.
        build_folder (str):     path to the build directory of your desired build version.
        load_exe_path (str):    filepath to a usable LoadFW executable.
        firmware_dir (str):     filepath to a directory that will house all of the firmware files.
        num_threads (int):      number of threads to open for multiprocessed firmware updates.
    Returns:
        None
    '''
    success = []
    fail = []
    param_list = []
    
    for iom in ioms:
        try:
            f_file = __get_pdna_firmware(iom, build_version, build_folder, firmware_dir)
        except Exception as e:
            log.LOG_LVL_2.warning('{} has no firmware file, skipping...'.format(iom))
            log.LOG_HEADER.debug('Exception: {}'.format(e))
            # This skip is not counted as a failure! Maybe this should be changed?
            continue
        else:
            param_list.append((iom, f_file, load_exe_path))

    with Pool(num_threads) as pool:
        results = pool.starmap(__update_pdna_fware_child, param_list)
        pool.close()
        pool.join()
    
    for i in results:
        if i[1]:
            success.append(i[0])
        else:
            fail.append(i[0])

    if len(fail) == 0:
        log.LOG_LVL_2.info('All PDNA IOMs have successfully updated their firmware!')
    else:
        log.LOG_LVL_2.critical('IOMs {} failed to update their firmware'.format(fail))


def update_all_pac_firmware(ioms: list):
    '''Not Implemented, Refer to Hagen Zhang's Co-op folder for more information'''
    log.LOG_LVL_1.fatal('PAC Firmware Updates have not been implemented yet! Exiting')
    for iom in ioms:
        iom.update_firmware_pac()

### ===============================================================================================
### HIDDEN HELPER FUNCTIONS =======================================================================

def __get_latest_build_version(pdna_installer_path: str):
    '''Retrieves the latest build version from the given installers path.
    
    This function should point to the path PowerDNA Installers directory inside the
    builder2 machine for the intended functionality.

    Args:
        pdna_installer_path (str): path to the "PowerDNA Installers" directory inside of builder2
    Returns:
        build_version (str):    latest build version found in builder2
        build_path (str):       filepath to the build folder
    '''
    try:
        valid_builds = []
            
        for file in os.listdir(pdna_installer_path):
            regex_pattern = re.compile(r'\d+\.\d+\.\d+')

            if regex_pattern.match(file):
                valid_builds.append(file)

        for n, i in enumerate(valid_builds):
            valid_builds[n] = version.parse(i)

        build_header = str(max(valid_builds))

        highest_version = 0
        build_folder_name = ''
        for file in os.listdir(os.path.join(pdna_installer_path, build_header)):
            regex_pattern = re.compile(r'\d+\.\d+\.\d+\.\d+_\d{4}-\d{2}-\d{2}')

            if regex_pattern.match(file):
                valid_builds.append(file)
                v = int(file.split('_')[0].split('.')[-1])

                if v > highest_version:
                    highest_version = v
                    build_folder_name = file

        build_version = build_header + '.' + str(highest_version)

        # returning the build version, then the build folder path
        log.LOG_LVL_2.info('Using build version {} for this run'.format(build_version))
        return build_version, os.path.join(pdna_installer_path, build_header, build_folder_name)
    except:
        log.LOG_LVL_1.fatal('No build version found! Killing the run...')
        raise FileNotFoundError('No valid build versions')


def __get_build_folder_from_version(build_version: str, pdna_installer_path: str):
    '''Retrieves a build folder given a build version.

    This function should point to the path PowerDNA Installers directory inside the
    builder2 machine for the intended functionality.

    Args:
        build_version (str):        build version to use
        pdna_installer_path (str):  path to the "PowerDNA Installers" directory inside of builder2
    Returns:
        filepath (str): filepath to the corresponding build folder
    Raises:
        ValueError: build version provided has no corresponding build folder available
    '''
    log.LOG_LVL_2.info('Build version {} specified, locating build folder...'.format(build_version))
    bh_split = build_version.split('.')
    build_header = '{}.{}.{}'.format(bh_split[0], bh_split[1], bh_split[2])
    
    for file in os.listdir(os.path.join(pdna_installer_path, build_header)):
        if file.startswith(build_version):
            log.LOG_LVL_3.info('Build folder located!')
            return os.path.join(pdna_installer_path, build_header, file)
        
    # if we get here, no valid build folder was found based on the given build version
    # so, we default to the most recent
    log.LOG_LVL_1.exception('No build folder found for build version {}!'.format(build_version))
    log.LOG_LVL_2.warning('Using the latest build version instead...')
    
    __, path = __get_latest_build_version(pdna_installer_path)
    return path


def __update_pdna_fware_child(
    iom: IOM,
    firmware_path: str,
    load_exe_path: str,
):
    '''Child function for update_all_iom_firmware. Used for multiprocessing.

    This function will attempt to update the firmware 3 times before giving up.
    If the update is successful, it will return True.

    Args:
        iom (IOM):              the IOM object to update.
        firmware_path (str):    firmware file to load into the IOM.
        load_exe_path (str):    filepath to a usable LoadFW executable.
    Returns:
        iom (IOM):      the IOM object that was updated.
        result (bool):  True of the firmware update was successful, else False.
    '''
    try:
        result, _ = iom.update_firmware_pdna(firmware_path, load_exe_path, attempts=3)
    except:
        return iom, -1
    else:
        return iom, result


def __get_pdna_firmware(iom: IOM, build_version: str, build_folder: str, dest: str):
    '''Retrieves the firmware file this IOM would use in PDNA mode (uC).

    The file retrieved will depend on the build folder path passed in.
    This path should lead to the location in builder2 where the build directory is located.

    After the firmware file is located, it will be sent to the given dest path,
    and return the path the file was moved to.

    Args:
        iom (IOM):              the IOM object to update.
        build_ver (str):        desired build version to update the IOM to.
        build_folder (str):     path to the build directory of your desired build version.
        dest (str):             directory to send the firmware file to.
    Returns:
        dest (str): filepath to the retrieved copy of the file firmware.
    '''
    firmware_dir = os.path.join(build_folder, 'Firmware')

    if iom.cpu == IOM.KEY_5200:
        fpath = os.path.join(firmware_dir, 'Firmware_PPC', 'romimage_{}.mot'.format(build_version.replace('.', '_')))
    
    # the 8347 CPUs all have the same firmware, but we keep the REV numbers seperate for future use.  
    elif iom.cpu == IOM.KEY_8347_1 or iom.cpu == IOM.KEY_8347_2 or iom.cpu == IOM.KEY_8347_3:
        fpath = os.path.join(firmware_dir, 'Firmware_PPC_1G', 'rom8347_{}.mot'.format(build_version.replace('.', '_')))

    elif iom.cpu == IOM.KEY_SOLOX:
        fpath = os.path.join(firmware_dir, 'Firmware_ARM_SOLOX', 'rom_arm_solox_{}.bin'.format(build_version.replace('.', '_')))

    else:
        raise NotImplementedError('Firmware support for {} CPUs have not been added yet!'.format(iom.cpu))

    # moving the firmware file
    local_firmware_file = os.path.join(dest, os.path.basename(fpath))
    return shutil.copy(fpath, local_firmware_file)

### ===============================================================================================




