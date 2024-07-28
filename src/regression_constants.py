'''regression_constants.py

File to store a bunch of constant values that will be used throughout the low-level regression run.
Each value should be specified carefully, as incorrect values can lead to broken runs.

NOTE: This file is merely a convenience tool. Each of these values are used as parameters, and can be 
      overwritten in the function call if desired. The definitions in this file should be modified with
      caution, since these values will be treated as the default
'''
import os

### =====================================================
### ===================== FILEPATHS =====================
### =====================================================
# Location of the PowerDNA Installers Folder.
PDNA_INSTALLERS_FOLDER = os.path.join('')

### ===============================
# Location of the LLR Code; this will influence all other filepaths below.
LLR_DIRPATH = r''

### ===============================
# Directory path (dirpath) of the master output folder. 
# Nested inside of this folder is where the output folder for individual runs will be stored.
MASTER_OUTPUT_PATH  = os.path.join(LLR_DIRPATH, 'output')

### ===============================
# Dirpath of the master resources folder. 
# All resource folders/files should be nested within this master folder (scripts, test sequences, etc).
MASTER_RESOURCE_PATH = os.path.join(LLR_DIRPATH, 'resources')

# Resource Filepaths: VM Scripts Master Dir / Test Sequences Master Dirs
SCRIPTS_DIR_FILEPATH = os.path.join(MASTER_RESOURCE_PATH, 'scripts')

BASIC_TEST_SEQUENCES_FILEPATH = os.path.join(MASTER_RESOURCE_PATH, 'basic_test_sequences')
FULL_TEST_SEQUENCES_FILEPATH = os.path.join(MASTER_RESOURCE_PATH, 'full_test_sequences')
LOGIC_REGRESSION_SEQUENCES_FILEPATH = os.path.join(MASTER_RESOURCE_PATH, 'logic_regression_sequences')

# Temporary Directory for the run. This is emptied each run, but you can stop that from
# happening for debugging purposes
TEMP_DIRECTORY_PATH = os.path.join(LLR_DIRPATH, 'temp')

### ======================================================
### ====================== DEVICES =======================
### ======================================================
### Device IP Prepend:
# All devices in the regression room should have an IPv4 address that starts with this value.
# The last number is the device number.
IP_PREPEND = '000.000.000'

### IOMs:
# Dict with each IOM being assigned to a CPU type
# NOTE: This must be up to date! Modify this each time the regression room changes.
#       There should be 0 duplicates
IOM_CPU_DICT = {
    '5200':     [],
    '8347_1':   [],
    '8347_2':   [],
    '8347_3':   [],
    'SOLOX':    [],
    'ZYNC':     [],
}

# All IOM Numbers:
IOMS = sorted(sum(IOM_CPU_DICT.values(), []))

# Which IOMs should be used for logic regression (based on IOM number)
LOGIC_REGRESSION_IOMS = [71]

### APC Numbers:
APCS = [202, 206]

### Agilent Numbers:
AGIS = [249, 252]


### ====================================================
### ===================== RUN TAGS =====================
### ====================================================
# These tags will serve as the message displayed on the website given 

# this will serve as the tag delimiter. the tag string should start with this and end with this as well.
# we automatically add in the first delim as soon as config['tags'] is initialized. adding in more tags
# should resemble: config['tags'] = config['tags'] + TAG
TAG_DELIM = '#'

# Special Tags: these are specially defined in the website code, Regression Webapp.
# If these tags are changed here, they must be changed in the website as well.
EXPECTED_TEST_TAG = lambda count: '--expected_{}{}'.format(count, TAG_DELIM)
ACTUAL_TEST_TAG = lambda count: '--actual_{}{}'.format(count, TAG_DELIM)
VM_TAG = lambda vm_list: '--vms_{}{}'.format(str(vm_list)[1:len(str(vm_list))-1].replace("'", ""), TAG_DELIM)
IOMS_OFF_TAG = lambda ioms: '--iomsoff_{}{}'.format(ioms, TAG_DELIM)

# General Tags: these tags will be displayed as-is on the website.
PAC_TAG = 'Ran in PAC mode' + TAG_DELIM
NO_FIRMWARE_TAG = 'Firmware Not Updated' + TAG_DELIM
ENCRYPTED_TAG = 'Ran on Secure Ports instead of Default Port' + TAG_DELIM
NO_HARDWARE_TAG = 'All Hardware Set To Disabled' + TAG_DELIM
INSTALL_SCRIPT_TAG = lambda vm_name: '{} Install Script Error'.format(vm_name) + TAG_DELIM
AUTOGEN_DIFF_TAG = lambda diff_list: 'AUTOGENDIFF Detected: {}'.format(diff_list)

### ======================================================
### ====================== VM_DICTS ======================
### ======================================================
# All VM dicts should have the following keys to ensure the test runs as intended:
# 'name':                   Name of the VM used in the run
# 'vm_snapshot':            Name of the VM snapshot to boot up
# 'install_script':         Filepath to the install script
# 'test_script':            Filepath to the testing script
# 'install_log':            Name of the install log file
# 'test_log':               Name of the test log file TODO
# 'vm_ip':                  IPv4 address for the VM
# 'username':               Username of the VM user account
# 'password':               Password of the VM user account
# 'home_dir':               Home directory of the VM (used to retrieve files from this location)
VM_DICTS = { 
    'linux_centos': {
        'name':             'Linux Tester CentOS',
        'short_name':       'centos',
        'vm_snapshot':      'CentOS Desktop',
        'install_script':   'resources\\scripts\\linux_install_script.sh',
        'test_script':      'resources\\scripts\\linux_regression_test_script.sh',
        'install_log':      'centos_install_log.txt',
        'test_log':         'centos_test_log.txt',
        'vm_ip':            '',
        'vm_port':          0,
        'username':         '',
        'password':         '',
        'home_dir':         '/home/tester',
    }, 
    'linux_fedora': {
        'name':             'Linux Tester Fedora',
        'short_name':       'fedora',
        'vm_snapshot' :     'Fedora Desktop',
        'install_script':   'resources\\scripts\\linux_install_script.sh',
        'test_script':      'resources\\scripts\\linux_regression_test_script.sh',
        'install_log':      'fedora_install_log.txt',
        'test_log':         'fedora_test_log.txt',
        'vm_ip':            '',
        'vm_port':          0,
        'username':         '',
        'password':         '',
        'home_dir':         '/home/tester',
    },
    'windows_10': {
        'name':             'Windows 10 Tester',
        'short_name':       'win10',
        'vm_snapshot' :     'Cleaner 17',
        'install_script':   'resources\\scripts\\win_install_script.bat',
        'test_script':      'resources\\scripts\\win_regression_test_script.bat',
        'install_log':      'win10_install_log.txt',
        'test_log':         'win10_test_log.txt',
        'vm_ip':            '',
        'vm_port':          0,
        'username':         '',
        'password':         '',
        'home_dir':         'C:\\User\\tester',
    },
    'windows_xp': {
        'name':             'Windows XP Tester',
        'short_name':       'winxp',
        'vm_snapshot' :     'Windows XP Desktop',
        'install_script':   'resources\\scripts\\win_install_script.bat',
        'test_script':      'resources\\scripts\\win_regression_test_script.bat',
        'install_log':      'winxp_install_log.txt',
        'test_log':         'winxp_test_log.txt',
        'vm_ip':            '',
        'vm_port':          0,
        'username':         '',
        'password':         '',
        'home_dir':         'C:\\Docume~1\\tester',
    }
}

# VMs that will run only the "basic" tests.
# This means that during the test phase, runs on these vms will include the -b flag for the testrunner, ensuring
# that only the power layer tests are completed.
BASIC_VMS = ['linux_fedora', 'windows_xp']

### ================================
### ======= LOGIC REGRESSION =======
### ================================
# Paths to logic files for updating logic
LOGIC_FILE_PATH = r''
OLD_LOGIC_FILE_PATH = r''

### ================================
### =========== DATABASE ===========
### ================================
JSON_RESULT_ARCHIVE_DIR = r''

# Dict of all possible statuses. Note that some of them seem like duplicates (Pass vs Passed),
# but this is intentional. This duplication is an unfortunate result from maintaining backwards
# compatability with the old test runner and compatibility with the current Framework Testsuite
# compilation process. Modern standards use Pass, but as of 07/01/2024 the Framework Testsuite
# still uses Passed
TEST_STATUS_DICT = {
    'pass_status':      ['Pass', 'Passed'],
    'neutral_status':   ['Warning'],
    'error_status':     ['Error', 'Fail', 'Failed', 'Fatal'],
    'off_status':       ['Off'],
    'skipped_status':   ['Skipped'],
    'wrong_os_status':  ['Wrong Embedded OS']
}


### ==================================
### ========== EXECUTABLES ===========
### ==================================
# Paths to executables used throughout low level regression.
# The paths to these may be variable from computer to computer

# Paths to C programs for updating logic
BUILD_COMMAND_LINE_EXE_PATH = os.path.join(LLR_DIRPATH, 'C_Programs', 'BuildCommandLine', 'Debug', 'BuildCommandLine.exe')
LOGIC_UPDATER_EXE_PATH = os.path.join(LLR_DIRPATH, 'C_Programs', 'AutomaticLogicUpdater', 'Debug', 'AutomaticLogicUpdater.exe')
SERIAL_NUMBER_EXE_PATH = os.path.join(LLR_DIRPATH, 'C_Programs', 'GetSerialNum', 'Debug', 'GetSerialNum.exe')

# C file located in PDNA_Utilities/LoadFW to load Firmware
LOAD_FIRMWARE_EXE = r''


### ================================
### ========== THREADING ===========
### ================================
IOM_THREADS = 60 
APC_THREADS = 8
AGI_THREADS = 8


### ===============================
### ============ MISC =============
### ===============================
# Flag used to indicate that the TestRunner detected a difference between the newly autogenerated XML
# and the provided XML from the TestSequences directory.
XML_DIFF_FLAG = 'AUTOGENDIFF'

# Flag used to indiciate that the Install Script had an error related to the installation of the
# software suite or sample building.
INSTALL_ERR_FLAG = 'INSTALLSCRIPTERROR'


if __name__ == '__main__':
    print('This file is not meant to be run as main! Exiting...')
