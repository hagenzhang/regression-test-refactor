'''low_level_tests.py

Contains the master function for running the Low Level Regression tests.
'''
import vboxapi

import regression_logger.log as log
import regression_constants as constants
import run_helpers.llr_h as llrh
import run_helpers.power as power
import regression_modules.vbox as vmc

def run_low_level_regression(
    config: dict,
    vm_dicts: dict = constants.VM_DICTS,
    basic_vms: list = constants.BASIC_VMS
):
    '''Runs the Low Level Regression tests on the IOMs in the Regression Room.

    A default run of the Low Level Regression testing process is as follows:
    Start off by booting up a VM. The VMs we boot up depend on the vm_dict and the config.
    We run on multiple OS's for more expansive coverage for our customers and to ensure 
    we don't have any OS related blindspots.

    Once we have booted up a VM, we will install the software suite via an ISO image we
    mount onto the VM. With the software suite successfully installed, we should also have
    the UEI TestRunner available. This step will also typically include building the sample
    code that comes with the UEI PowerDNA installer.

    Once the install process is complete, we enter the testing process. This process will
    involve sending over an XML to the VM (which is how we represent a sequence of tests),
    running the XML on the UEI TestRunner, and then retrieving the results / test logs.
    Depending on the VM we are running, we will either run all of the tests for a given
    layer, or only the power layer tests (AKA the "basic" tests). This is to try and
    make sure our software can still interact with the IOMs while trying to minimize the
    runtime of the testing process. The IOMs that we interact with are all located inside
    of the Regression Room, and the specific IOMs will depend on which XMLs we send over.
    If we wish to run tests on a given IOM, we must send over an XML test sequence with an
    IP that corresponds to that IOM. Note that we assume each XML will correspond to one IP
    address (even though technically an XML can run tests on multiple IPs).

    After the testing process is over, we will typically shutdown the current VM, and then
    move onto the next one. Once all of the VMs have been iterated through, then the low
    level regression testing process is complete. The VMs which the run chooses to iterate 
    through are determined by the run flags.

    Args:
        config (dict):      configuration dictionary to determine the run's behavior.
        vm_dicts (dict):    a dictionary of VM dictionaries (refer to the constants file).
        basic_vms (list):   a list of VMs to run the basic tests on.
                            note that each of the VMs are identified by their keys according
                            to the vm_dicts parameter provided.
    Returns:
        None
    '''
    log.LOG_HEADER.info('========= Running Regression Tests =========')
    vbox_manager: vboxapi.VirtualBoxManager = vboxapi.VirtualBoxManager(None, None)

    # loop through each of the VMs in the run configuration for each test
    for vm_key in config['vms']:
        current_vmdict = vm_dicts[vm_key]

        # if no vmdict exists for a given VM key, that means it is not valid
        if not current_vmdict:
            log.LOG_LVL_1.error('VM key {} is invalid, skipping...'.format(vm_key))
            continue

        # create the vboxapi objects necessary to control the VMs
        vbox, vm, vsession = vmc.create_vm_controllers(vbox_manager, current_vmdict['name'])

        basic_only = vm_key in basic_vms

        if not config['headlessstart']:
            log.LOG_HEADER.info('') # used as a spacer in the logs, looks cleaner than using \n
            log.LOG_LVL_1.info('===== Starting VM {}'.format(current_vmdict['name']))
            if basic_only:
                log.LOG_LVL_1.info('**BASIC_VM_DETECTED: The following VM will not build samples and only run power layer tests!')
            
            llrh.vm_startup(
                vm          = vm,
                vmanager    = vbox_manager,
                vbox        = vbox,
                vsession    = vsession,
                vm_dict     = current_vmdict,
                config      = config,
            )
            log.LOG_LVL_1.info('=== VM startup process completed\n')

            log.LOG_LVL_1.info('=== Running install process')
            llrh.run_install(
                vm      = vm,
                vbox    = vbox,
                vm_dict = current_vmdict,
                config  = config,
                samples = not basic_only) # True when the VM is NOT a "basic VM"
            log.LOG_LVL_1.info('=== Install process completed\n')
        

        if not config['notest']:
            log.LOG_LVL_1.info('=== Running test process')
            llrh.run_test(
                vm                  = vm,
                vbox                = vbox,
                vm_dict             = current_vmdict,
                config              = config,
                basic_tests_only    = basic_only)
            log.LOG_LVL_1.info('=== Test process completed\n')
        
    
        if not config['noshutdown']:
            log.LOG_LVL_1.info('=== Running shutdown process')
            llrh.run_shutdown(vbox_manager, vm, vsession)
            log.LOG_LVL_1.info('=== Shutdown process completed\n')

        # we want to power-cycle just in case something went wrong in one of the tests and it
        # leaves the IOM in a bad state
        if not config['nopower']:
            log.LOG_LVL_1.info('Power-cycling IOMs')
            config['active_apcs'], _ = power.cycle_apcs(config['active_apcs'])

            log.LOG_LVL_1.info('Checking IOM activity')
            config['active_ioms'], _ = power.ping_all_ioms(config['active_ioms'])

    log.LOG_HEADER.info('======== Regression Tests Completed ========\n')