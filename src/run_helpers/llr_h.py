'''llr_h.py

Low Level Regression Helpers.

Contains the helper functions for the Low Level Regression testing process.
'''

from copy import deepcopy
import os
import time
import paramiko
import paramiko.buffered_pipe
import socket

from multiprocessing import Pool

import regression_logger.log as log
import regression_constants as constants
import regression_modules.vbox as vmc
from regression_modules.testrunner_file import UeiTestXMLParser
from regression_modules.testrunner_file import UeiResultJSONParser

### ===============================================================================================
### BASIC HELPER FUNCTIONS ========================================================================
def __command_formatter(scriptname: str, args: str, os_family: str):
    '''Writes a command based on the os type given the scriptname to run and the run args.
    
    Args:
        scriptname (str):   path to the script you want to run.
        args (str):         the arguments for the script.
        os_family (str):    vbox OS family (derived by `vbox.getGuestOSType(vm.OSTypeId).familyDescription`)
    Returns:
        command (str): the command formatted for the given os.
    '''
    if "Microsoft Windows" == os_family:
        return 'cmd.exe /C {} {}'.format(scriptname, args)
    elif "Linux" == os_family or "Other" == os_family:
        return 'chmod +x {};./{} {}'.format(scriptname, scriptname, args)
    else:
        raise NotImplementedError('The current os family {} not recognized'.format(os_family))


def get_iso_path(build_ver: str, build_folder: str, os_family: str):
    '''Retrieves the filepath for the PowerDNA ISO image used in the vbox VMs.
    
    Args:
        build_version (str):    build version of the run.
        build_folder (str):     filepath to the corresponding build folder in builder2.
        os_family (str):        vbox OS family (derived by `vbox.getGuestOSType(vm.OSTypeId).familyDescription`)
    Returns:
        iso_path (str): string filepath to the proper ISO image.
    '''
    # NOTE: Currently only supports Linux / Windows VMs
    if os_family == "Microsoft Windows" or os_family == "Linux":
        iso_name = "PowerDNA_Win_Linux_" + build_ver + ".iso"
    else:
        raise NotImplementedError('Support for Non Linux / Windows VMs have not been added yet!')
    
    # pardir = parent directory (in most cases, '..' is used in the path)
    iso_path = os.path.abspath(os.path.join(build_folder, os.pardir, iso_name))
    if os.path.isfile(iso_path):
        log.LOG_LVL_2.info('ISO Located at: {}'.format(iso_path))
        return iso_path
    else:
        log.LOG_LVL_1.exception('No ISO found based on the iso path!')
        raise FileNotFoundError('No valid ISO found at {}'.format(iso_path))
    
### ===============================================================================================
### LLR PHASES ====================================================================================
def vm_startup(
    vm,
    vmanager,
    vbox,
    vsession,
    vm_dict: dict,
    config: dict,
):
    '''Starts the given VM up, and mounts an installer ISO.

    The ISO used will be determined by the build version in the configuration

    Args:
        vm:             VirtualBox virtual machine
        vmanager:       VirtualBoxManager
        vbox:           VirutalBox singleton object
        vsession:       VirtualBox VM session
        vm_dict:        VM information dictionary
        config (dict):  configuration dictionary to determine the run's behavior.
    Returns:
        None
    '''
    log.LOG_LVL_2.info('Retrieving ISO...')
    os_family = vbox.getGuestOSType(vm.OSTypeId).familyDescription        
    iso_path = get_iso_path(config['build_version'], config['build_folder'], os_family) 
    
    log.LOG_LVL_2.info('Starting VM {}{}'.format(vm_dict['name'], 
        str(' with snapshot {}'.format(vm_dict['vm_snapshot']) if vm_dict['vm_snapshot'] else '')))
    
    vmc.start_vm( # BF needs full revisit, possible rewrite, error codes should be caught and analyzed (error handling!!)
        vname       = vm_dict['name'],
        vmanager    = vmanager,
        vbox        = vbox,
        vm          = vm,
        vsession    = vsession,
        snapshot    = vm_dict['vm_snapshot'])
    
    log.LOG_LVL_2.info('Mounting the ISO at {}'.format(iso_path))
    vmc.mount_iso(iso_path, vmanager, vbox, vm, vsession)
    time.sleep(15) # waits for ISO to finish mounting


def run_install(
    vm,
    vbox,
    vm_dict: dict,
    config: dict,
    samples: bool = False,
    script_timeout: int = 1024,
):
    '''Runs the install process for the current VM.

    The install process starts off by formatting the command that will be used.
    Then, it sends over the command via ssh client and records the stdout and stderr.

    Args:
        vm:                     VirtualBox virtual machine.
        vbox:                   VirutalBox singleton object.
        vm_dict:                VM information dictionary.
        config (dict):          configuration dictionary to determine the run's behavior.
        script_timeout (int):   timeout for the install script, in seconds.
        temp_dir (str):         filepath to a temporary directory to dump files.
    Returns:
        None
    '''
    # =========================================================================================
    # Creating the directory to place the install log.
    install_log_path = os.path.join(config['run_vm_logs'], vm_dict['short_name'])
    os.makedirs(install_log_path)

    # =========================================================================================
    # Placing the install script on the VM
    scriptname = os.path.basename(vm_dict['install_script'])
    
    try:
        vmc.put_file_on_vm(vm_dict['vm_ip'], vm_dict['vm_port'],
                           vm_dict['username'], vm_dict['password'],
                           vm_dict['install_script'], scriptname)
    except Exception as e:
        log.LOG_LVL_1.fatal('Failed to move install script over, quitting install step')
        log.LOG_LVL_2.fatal('Error:\n{}'.format(e))
        return
    
    # =========================================================================================
    # Writing the install command to run on the VM.

    # COMMAND FORMAT: ./scriptname BUILD logfilename.txt -s
    #                  ^ arg0      ^arg1   ^arg2         ^optional arg3
    # example for installer + building the samples (a full run in development version): ./scriptname 5.3 logfile.txt -s
    # example for just the installer: ./scriptname 5.2 logfile.txt
    bv: str = deepcopy(config['build_version'])
    build_num = bv[:bv.find('.', bv.find('.') + 1, len(bv))] # example: derives '5.3' from '5.3.0.x'
    
    # we add in a -s flag if we want to build the code samples
    args = build_num + ' ' + vm_dict['install_log'] + (' -s' if not config['nosamples'] and samples else '')

    try:
        command = __command_formatter(scriptname, args, vbox.getGuestOSType(vm.OSTypeId).familyDescription)
    except:
        log.LOG_LVL_1.critical('Invalid os_family, skipping install process...')  
        return
     
    # =========================================================================================
    # Executing the actual command to run the install script on the VM.
    log.LOG_LVL_2.info('Running command "{}"'.format(command))
    if script_timeout:
        log.LOG_LVL_3.info('timeout: {} seconds'.format(script_timeout))

    start_time = time.time()
    try:
        _, stderr, status = vmc.run_command_ssh(vm_dict['vm_ip'], vm_dict['vm_port'],
                                                vm_dict['username'], vm_dict['password'], 
                                                command, script_timeout)
    except Exception as e:
        log.LOG_LVL_1.critical('An error occurred while running the install command: \n{}'.format(e))
    else:
        if stderr:
            log.LOG_LVL_2.error('stderr detected! Exit code: {}, stderr:\n{}'.format(status, stderr))
    
    exec_time = round(time.time() - start_time, 2)
    
    # =========================================================================================
    # Retrieving the log file.
    try:
        log.LOG_LVL_3.info('Retrieving install script log {}'.format(vm_dict['install_log']))
        loc = vmc.get_file_from_vm(vm_dict['vm_ip'], vm_dict['vm_port'],
                                   vm_dict['username'], vm_dict['password'],
                                   vm_dict['install_log'], os.path.join(install_log_path, vm_dict['install_log']))
    except Exception as e:
        log.LOG_LVL_2.error('Install script log could not be retrieved! Tried to get: {}'.format(vm_dict['install_log']))
        log.LOG_LVL_2.exception('Exception: \n{}'.format(e))
    else:
        log.LOG_LVL_3.info('Install script log moved to {}'.format(loc[len(os.getcwd()):]))
        
        with open(loc) as file: # parse for the INSTALLSCRIPTERROR flag
            for line in reversed(list(file)):
                if constants.INSTALL_ERR_FLAG in line:
                    log.LOG_LVL_3.info('**Install Script Error Detected!')
                    config['tags'] = config['tags'] + constants.INSTALL_SCRIPT_TAG(vm_dict['name'])
                    break
    
    log.LOG_LVL_2.info('Install command completed in {} seconds'.format(exec_time))
    # =========================================================================================


def run_test(
    vm,
    vbox,
    vm_dict: dict,
    config: dict,
    script_timeout: int = 3600,
    basic_tests_only: bool = False,
    basic_xml_dirpath: str = constants.BASIC_TEST_SEQUENCES_FILEPATH,
    full_xml_dirpath: str = constants.FULL_TEST_SEQUENCES_FILEPATH,
):
    '''Runs the test process for the current VM test.
    
    The test process works by sending over an XML, running the test script on that one XML,
    and then retrieving the results of that one test sequence. We run this process until we've
    tested all of the XMLs inside of the sequences directory specified.

    Some VMs are set to only run power layer tests (AKA "basic" tests). This is used simply
    as a means of ensuring the software works at a basic level and can save time. 

    Args:
        vm:                         VirtualBox virtual machine.
        vbox:                       VirutalBox singleton object.
        vm_dict:                    VM information dictionary.
        config (dict):              configuration dictionary to determine the run's behavior.
        script_timeout (int):       timeout for the install script, in seconds.
        basic_tests_only (bool):    True if we are only running basic tests, else False.
        basic_xml_dirpath (str):    filepath to the basic test sequences directory.
        full_xml_dirpath (str):     filepath to the normal test sequences directory.
        temp_dir (str):             filepath to a temporary directory to dump files.
    Returns:
        None
    '''
    # =========================================================================================
    # Creates directories for the JSON results and the testrunner logs.
    test_result_dir = os.path.join(config['run_vm_results'], vm_dict['short_name'])
    testrunner_log_dir = os.path.join(config['run_vm_logs'], vm_dict['short_name'], vm_dict['short_name'] + '_testrunner_logs')
    scriptname = os.path.basename(vm_dict['test_script'])

    # create the result dir for this VM
    os.mkdir(test_result_dir)

    # create the testrunner log dir for this VM
    os.makedirs(testrunner_log_dir)

    # =========================================================================================
    # Placing the test script on the VM.
    try:
        vmc.put_file_on_vm(vm_dict['vm_ip'], vm_dict['vm_port'], 
                           vm_dict['username'], vm_dict['password'],
                           vm_dict['test_script'], scriptname)
    except:
        log.LOG_LVL_1.critical('Error occurred trying to move the test script to the VM, exiting!')
        return
    
    # =========================================================================================
    # Sets which XMLs we are and creates a list of IOM numbers from the active ioms list.
    xmls_path = basic_xml_dirpath if basic_tests_only else full_xml_dirpath

    # Since we store a list of IOM objects, we now need to pull out the IOM Device Numbers
    iom_dev_nums = [i.host_num for i in config['active_ioms']]

    # =========================================================================================
    # Looping through the XMLs in the specified directory

    # TODO: we can probably parallelize this step?
    # There is a danger of writing to one log file with parallelization
    for xml in os.listdir(xmls_path):
        log.LOG_HEADER.info('') # used as a spacer in the logs, looks cleaner than using \n

        # These values will be compared later
        xml_test_count = 0
        json_result_count = 0 

        # === Derives the IP address of the XML file ==========================================
        test_xml = UeiTestXMLParser(os.path.join(xmls_path, xml))
        try:
            xml_ip = test_xml.get_global_ip()
        except:
            log.LOG_LVL_1.fatal('Unable to derive IP from xml {}, skipping...'.format(xml))
            continue
        ip_device_num = int(xml_ip.split('.')[-1])

        # === Skips an XML if the IP is set to be skipped in the config =======================
        log.LOG_LVL_2.info('XML Test IP Num: {}'.format(xml_ip))
        if ip_device_num not in iom_dev_nums:
            log.LOG_LVL_3.warning('IOM number {} is not active, skipping test...'.format(ip_device_num))
            continue

        # === Adds in the UDP Port Property if specified in the config ========================
        if config['sslport']: # if true, we are using the secure port instead of the default port!
            log.LOG_LVL_3.info('Running tests on secure ports instead of the default port!')
            test_xml.add_udp_port()
            test_xml.write_to_file(test_xml.path)

        # === Sets the name of the resulting files from the test run ==========================
        test_result = '{}_test_101_{}_result.json'.format(vm_dict['short_name'], ip_device_num)
        testrunner_log = '{}_101_{}.txt'.format(vm_dict['short_name'], ip_device_num)

        # === Places the current XML file onto the VM =========================================
        try:
            vmc.put_file_on_vm(vm_dict['vm_ip'], vm_dict['vm_port'],
                               vm_dict['username'], vm_dict['password'], 
                               test_xml.path, xml)
        except:
            log.LOG_LVL_2.critical('Error occurred trying to move {} to the VM, skipping...'.format(xml))
            continue

        # === Formats the test command to send to the VM ======================================
        # Test Script Arguments:
        #           arg1        arg2                arg3              optional arg4
        exec_args = xml + ' ' + test_result + ' ' + testrunner_log + (' -b' if basic_tests_only else '')
        try:
            command = __command_formatter(scriptname, exec_args, vbox.getGuestOSType(vm.OSTypeId).familyDescription)
        except:
            log.LOG_LVL_1.critical('Invalid os_family, skipping test process...')  
            return

        # === Running the test script =========================================================
        try:
            start_time = time.time()
            _, stderr, _ = vmc.run_command_ssh(vm_dict['vm_ip'], vm_dict['vm_port'],
                                               vm_dict['username'], vm_dict['password'], 
                                               command, timeout=script_timeout)
            exec_time = round(time.time() - start_time, 2)
            log.LOG_LVL_3.info('IOM {} test command completed in {} seconds{}'.format(xml_ip, exec_time, (', stderr detected!' if stderr else '')))
        except socket.timeout:
            log.LOG_LVL_2.error('Test script run hit the timeout!')                
            continue
        except paramiko.SSHException as e:
            log.LOG_LVL_2.error('An error occurred while running the test command: {}'.format(e))
            continue
        
         # === Retrieving the testrunner log txt file ==========================================
        try:
            log.LOG_LVL_3.info('Retrieving testrunner logs {}'.format(testrunner_log))
            loc = vmc.get_file_from_vm(vm_dict['vm_ip'], vm_dict['vm_port'],
                                       vm_dict['username'], vm_dict['password'], 
                                       testrunner_log, testrunner_log_dir)
        except Exception as e:
            log.LOG_LVL_2.error('Testrunner log file could not be retrieved! Tried to get: {}'.format(testrunner_log))
            log.LOG_LVL_2.exception('Exception: {}'.format(e))
        else:
            with open(loc) as file: # parse for the AUTOGEN flag
                for line in file:
                    if constants.XML_DIFF_FLAG in line:
                        log.LOG_LVL_3.info('**AUTOGEN DIFF DETECTED! Changes detected in XML {}'.format(xml))
                        config['autogen_diff_xmls'] += [ip_device_num]
                        break
            log.LOG_LVL_3.info('Testrunner logs moved to {}'.format(loc[len(os.getcwd()):]))

        # === Retrieving the result JSON ======================================================
        try:
            log.LOG_LVL_3.info('Retrieving test result json {}'.format(test_result))
            loc = vmc.get_file_from_vm(vm_dict['vm_ip'], vm_dict['vm_port'],
                                       vm_dict['username'], vm_dict['password'], test_result, test_result_dir)
            log.LOG_LVL_3.info('Test result json moved to {}'.format(loc[len(os.getcwd()):]))
            
        except Exception as e:
            log.LOG_LVL_2.error('Test result file could not be retrieved! Tried to get: {}'.format(test_result))
        else:
            # this is necessary since the resulting JSON from a test run can sometimes be malformed due to
            # an error mid test. Any malformed JSON will not be read correctly and will be discarded.
            try:
                json_result_count =  UeiResultJSONParser(loc).num_tests() # update the JSON result count
            except:
                log.LOG_LVL_2.critical('Test JSON was malformed, discarding results!')
            else:
                config['actual_test_count'] = config['actual_test_count'] + json_result_count

        # === Retrieving the new XML file =====================================================
        try:
            log.LOG_LVL_3.info('Retrieving test xml {}'.format(xml))
            loc = vmc.get_file_from_vm(vm_dict['vm_ip'], vm_dict['vm_port'],
                                       vm_dict['username'], vm_dict['password'],
                                       xml, test_xml.path)
            log.LOG_LVL_3.info('New test xml moved to {}'.format(loc[len(os.getcwd()):]))
        except Exception as e:
            log.LOG_LVL_2.error('Test XML file could not be retrieved! Tried to get: {}'.format(xml))
            log.LOG_LVL_2.exception('Exception: {}'.format(e))
        else:
            test_xml.__init__(loc) # re-initializes the object to the new xml in case it changed\
            xml_test_count = test_xml.num_tests() # update the XML test count variable
            config['expected_test_count'] = config['expected_test_count'] + test_xml.num_tests()

            # Ensure that the udp port property is not in the stored XMLs
            test_xml.remove_udp_port()
            test_xml.write_to_file(loc)
            pass

        # === Compare Num Tests vs Num Results ===============================================
        if xml_test_count != json_result_count:
            log.LOG_LVL_3.warning('Discrepancy Between Test Count and Result Count Found!')
            log.LOG_LVL_3.warning('Test Count: {}, Result Count: {}'.format(xml_test_count, json_result_count))

    # =========================================================================================


def run_shutdown(
    vmanager,
    vm,
    vsession,
):
    '''Shuts down the given VirtualBox VM.
    
    Args:
        vmanager:   VirtualBoxManager.
        vm:         VirtualBox virtual machine.
        vm_dict:    VM information dictionary.
    Returns:
        None
    '''
    vmc.shutdown_vm(vmanager, vm, vsession)

### ===============================================================================================