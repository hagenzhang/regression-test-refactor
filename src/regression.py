'''low_level_regression.py

Main method of the Low Level Regression testing program.

Instantiates the parameters of the Low Level Regression test based on the provided
command line arguments. 
Then, runs each step of the test run according to those parameters.

More information can be found in the README and USEME
'''
import argparse
import sys
from tendo import singleton

import regression_constants as constants

import default_run.setup as setup
import default_run.low_level as regression
import default_run.teardown as teardown

if __name__ == '__main__':
    # Close program if it is already running elsewhere
    try:
        singleton.SingleInstance()
    except singleton.SingleInstanceException:
        sys.exit('Regression Test is already running, closing this instance')
    
    # argparser takes in the command line arguments and stores them.
    # depending on the arguments that you pass in, the behavior of the test run
    # will change.
    #
    # default values are all intended for a full run-through of the regression tests on the latest development version,
    parser = argparse.ArgumentParser()
    parser.add_argument('--nosamples',          action='store_true',    help='skips building the sample libraries in the install phase')
    parser.add_argument('--nopower',            action='store_true',    help='skips all interactions with the IOMs (pinging, powercycling, etc)')
    parser.add_argument('--headlessstart',      action='store_true',    help='skips the startup and install steps on each VM')
    parser.add_argument('--notest',             action='store_true',    help='skips running the test step on each VM')
    parser.add_argument('--noshutdown',         action='store_true',    help='skips the shutdown on each VM')
    parser.add_argument('--nodb',               action='store_true',    help='skips uploading the test results to the database')
    parser.add_argument('--nofirmwareupdate',   action='store_true',    help='skips updating board firmware')
    parser.add_argument('--vms',                nargs='*',              help='sets which VMs to activate & test: refer to README', default=list(constants.VM_DICTS.keys()))
    parser.add_argument('--active_ioms',        nargs='*',  type=int,   help='active IOMs for the test run', default=constants.IOMS)
    parser.add_argument('--active_apcs',        nargs='*',  type=int,   help='active APCs for the test run', default=constants.APCS)
    parser.add_argument('--active_agis',        nargs='*',  type=int,   help='active Agilents for the test run', default=constants.AGIS)
    parser.add_argument('--build_version',      type=str,               help='build version to use (example: 5.2.0.8, 5.3.0.30)', default=None)
    parser.add_argument('--sslport',            action='store_true',    help='runs the tests using the DAQ SSL ports instead of the default port')
    parser.add_argument('--noxmlcommit',        action='store_true',    help='skips committing the test sequence XMLs to subversion')
    parser.add_argument('--pac',                action='store_true',    help='sets regression to run in PAC mode instead of PDNA')

    args = parser.parse_args()
    # =============================================================================================
    # Run the setup for the tests. 
    # This will yield the configuration dictionary to be used for the rest of the run.
    config = setup.run_setup(vars(args))
    
    # Runs Low Level Regression tests on VirtualBox VMs.
    # This step can be divided into 4 phases for each VM: startup, install, test, and shutdown
    regression.run_low_level_regression(config)
    
    # Runs cleanup process.
    teardown.run_teardown(config) # BF needs full refactor, can be done in Q3

