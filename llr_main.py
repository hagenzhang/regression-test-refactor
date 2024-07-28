'''run_test.py

This script is meant to initiate a run of the Low-Level Regression testing script.
Refer to the README for additional details.

To Run:
conda activate regression
python ./llr_main.py

NOTE: This code is not subversioned!
'''
import subprocess
import svn.local

import src.regression_constants as constants

# ========================================================================================================================
# ========================================================================================================================
# ========================================================================================================================

def main():
     '''Main Method, updates the src dir and starts the selected run type'''
     run_updates()
     run_default()

# ========================================================================================================================
# ========================================================================================================================
# ========================================================================================================================


def run_updates():
     '''Updates all of the ReleaseTest files using svn update'''

     print("Updating the Regression Testing scripts...")
     print("This should be fixed when this code is subversioned!")

     try:
          client = svn.local.LocalClient(constants.LLR_DIRPATH)
          client.update()
     except Exception as e:
          print('SVN Updating Failed, exception:\n{}'.format(e))
     else:
          print('SVN Updating Successful')


def run_default():
     '''Initiates the default Regression Test run'''
     subprocess.call(r'python .\src\regression.py', shell=False, cwd=constants.LLR_DIRPATH)


if __name__ == '__main__':
     '''Entry point for the start_regression script'''
     main()