'''teardown.py

Contains the master function for running the teardown / cleanup process
'''
import os
import svn.local

import regression_logger.log as log
import regression_constants as constants
import run_helpers.tdown_h as tdh
import run_helpers.power as power

def run_teardown(
    config: dict,
    basic_xml_dirpath: str = constants.BASIC_TEST_SEQUENCES_FILEPATH,
    full_xml_dirpath: str = constants.FULL_TEST_SEQUENCES_FILEPATH,
    temp_directory: str = constants.TEMP_DIRECTORY_PATH,
):
    '''Runs the teardown process for this Low Level Regression Run.

    This process wraps up the Low Level Regression run and does any necessary cleanup.
    This inculdes (by default):
    1) Powering off all of the hardware in the regression room
    2) Merging all of the result JSONs for the database 
    3) Committing the newly generated XMLs to subversion
    4) Emptying the temp directory
    5) Any other misc. file cleanup.

    Args:
        config (dict):          configuration dictionary to determine the run's behavior.
        temp_directory (str):   filepath for the temp directory used for the run.
    Returns:
        None
    '''
    log.LOG_HEADER.info('======== Running Teardown Process ========')

    ### Final Tag Additions:
    config['tags'] = config['tags'] + constants.EXPECTED_TEST_TAG(config['expected_test_count'])
    config['tags'] = config['tags'] + constants.ACTUAL_TEST_TAG(config['actual_test_count'])
    
    off_ioms = sorted(list(set(config['initial_ioms']) - set([i.host_num for i in config['active_ioms']])))
    if len(off_ioms) > 0:
        config['tags'] = config['tags'] + constants.IOMS_OFF_TAG(off_ioms)

    autogen_ioms = sorted(list(set(config['autogen_diff_xmls'])))
    if len(autogen_ioms) > 0:
        config['tags'] = config['tags'] + constants.AUTOGEN_DIFF_TAG(autogen_ioms)
    
    ### Power Down:
    # turn off all the hardware in the regression room
    if not config['nopower']:
        # turn off IOMS and Dongles (turn off Agilents first, then APCs)
        log.LOG_LVL_1.info('Powering off the Regression Room Hardware...')
        power.power_off_hardware(config['active_apcs'], config['active_agis'])

    ### JSON Combination:
    # creating the combined results JSON file used to update the database
    if not config['nodb']:
        log.LOG_LVL_1.info('Merging test result JSON files (for database upload)')
        tdh.combine_results(config)

    ### SVN XMLs:
    # subversion commit the new XMLs generated from the testrunner
    if not config['noxmlcommit']:
        log.LOG_LVL_1.info('Committing XMLs to Subversion')
        svn_repo_path = os.path.join(constants.LLR_DIRPATH)
        
        # instantiate a local SVN client for our repo
        client = svn.local.LocalClient(svn_repo_path)
        client.commit(message='Low Level Regression XML update', rel_filepaths=[basic_xml_dirpath, full_xml_dirpath])

    ### File Cleanup:
    # wipe the temp directory
    log.LOG_LVL_1.info('Emptying temp directory')
    for file in os.listdir(temp_directory):
        os.remove(os.path.join(temp_directory, file))

    ### Closing Prints:
    # printing the config (mostly for debug / developer use)
    log.LOG_LVL_1.info('Config Dict:')
    for k, v in config.items():
        log.LOG_LVL_2.debug('key: {}, value: {}'.format(k, v)) 

    log.LOG_HEADER.info('======== Teardown Completed ========')
    log.LOG_HEADER.info('Low Level Regression Run Completed')
    log.close_logs()


