'''tdown_h.py

Teardown Helpers.

Contains the helper functions used in teardown process of the regression run.
Hagen: This code is from the old system and in dire need of a full re-write. 
Everything in this file is questionable and could probably be improved a lot both in functionality and readability.

I highly recommend testing a new implementation heavily before modifying this code, since it's very
crucial to the system.
'''
import os
import csv

from datetime import datetime

import regression_logger.log as log
import regression_constants as constants

def combine_results(
    config: dict,
    json_archive_dir: str = constants.JSON_RESULT_ARCHIVE_DIR,
    test_status_dict: dict = constants.TEST_STATUS_DICT,
    vm_dicts: dict = constants.VM_DICTS
):
    '''Merges all of the run result json files for the Regression Database
    
    This function is extremely long and unwieldy, since it's been minimally edited from the original
    Low Level Regression python code. This functionality is critical to the system, if you wish to
    proceed with modifications / improvements then proceed with caution.
    
    Args:
        config (dict):              the configuration dictionary of this run.
        json_archive_dir (str):     directory to send the combined JSON file to.
        test_status_dict (dict):    dictionary of all possible test statuses and how they rank.
        vm_dicts (dict):            a dictionary of VM dictionaries (refer to the constants file).
    '''
    result_path = config['run_directory']

    os_list = config['vms']
    logic_results_dir = config['run_logic_results']
    
    # If we ran zero os's and no logic regression, we can skip
    if len(os_list) == 0 and not os.path.exists(logic_results_dir):
        log.LOG_HEADER.debug('skipping database upload...')
        return

    #Sets date/time to be used in file
    date = str(datetime.now())
    stringdate = date[:date.find('.')]
    
    fileString = stringdate.replace(':', '-').replace(' ', '_')
    # This output file is where we will be merging all of the result JSONs
    outputfile = os.path.join(json_archive_dir, fileString + '.json')
    
    # ===============================================================
    # Now, we merge all of the results together:
    highest_key = 1
    json_data_combined = '' # output to final json file
    test_result_status = test_status_dict['skipped_status'][0] # skipped is our default state

    # Holds primary keys, status, and name per chassis
    chassis_key = dict()
    chassis_status = dict()
    chassis_name = dict()

    # Holds primary keys per OS per chassis
    os_key = dict()
    os_status = dict()

    # Creates lists for ip and files per OS
    ip_per_os = []
    file_per_os = []

    # Holds files already in the database for each OS
    all_os_objects = '\n'
    os_file_in_db = []

    # Holds date object primary key
    date_key = highest_key
    highest_key += 1

    # If there are hardware regression tests
    if os.path.exists(logic_results_dir):
        for filepath in os.listdir(logic_results_dir):
            #Get data from the file
            with open(os.path.join(logic_results_dir, filepath)) as data_file:
                data = data_file.read()
                json_data_combined += data
    
    # If there are OSs in osList
    if len(os_list) != 0:
        # Initialize for each OS
        for osName in os_list:
            ip_per_os.append([])
            file_per_os.append([])
            os_file_in_db.append(dict())

        # Checks each result file to see that it has an IP, is a JSON, and is not in the database
        for idx, os_name in enumerate(os_list):
            os_result_path = os.path.join(result_path, 'vm_results', vm_dicts[os_name]['short_name'])
            file_per_os[idx], os_file_in_db[idx], ip_per_os[idx] = getFilesAndIP(os_result_path)

        # above 2 for loops can probably be combined?
        all_chassis = ip_per_os[0]
        ip_in_all = ip_per_os[0]
        
        # Gets the union and itersection of the IP lists
        # This ensures that all chassis are accounted for and no duplicates are made
        # ipInAll was previously used to prevent duplicate chassis creation; no longer needed?
        for idx in range(len(os_list) - 1):
            all_chassis = list(set(all_chassis) | set(ip_per_os[idx + 1]))
            ip_in_all = list(set(ip_in_all) & set(ip_per_os[idx + 1]))
            
        fileCount = 0
        for fileSet in file_per_os:
            fileCount += len(fileSet)

        if fileCount == 0:
            log.LOG_HEADER.debug('File Count is 0!')
            pass

        # Sets aside primary keys for Chassis and OS
        for ip in all_chassis:
            chassis_key[ip] = highest_key
            highest_key += 1

            # Create placeholder in chassisStatus dictionary, with best possible status
            chassis_status[ip] = test_status_dict['skipped_status'][0]

            # Placeholder in chassisName
            chassis_name[ip] = ''

            for idx, osName in enumerate(os_list):
                if ip in ip_per_os[idx]:
                    os_key[osName + ip] = highest_key
                    os_status[osName + ip] = test_status_dict['skipped_status'][0]
                    highest_key += 1

        # Pull results from each result file per OS
        for idx, osName in enumerate(os_list):
            for filename in file_per_os[idx]:
                # The file was already added to the database, don't add it to the JSON
                # This should only occur if tests are not run
                if os_file_in_db[idx][filename] == True:
                    continue # skips current iteration
                
                # Create path to OS file
                filepath = os.path.join(result_path, 'vm_results', vm_dicts[osName]['short_name'], filename)

                # Get data from the file
                with open(filepath, 'r') as data_file:
                    data = data_file.read()
                ip = getIP(filename)

                # Remove NUL characters from data if present (these are std::ends characters in C/C++)
                data = data.replace('\0', '')

                # Get all data models from the result file and update status as needed 
                # TODO: There was a "CHANGE THIS" note here originally but it never stated what should be improved,
                # so this code remains unchanged
                ret = addModels(data, highest_key, os_key[osName + ip], osName)
                json_data_combined += ret[0]
                highest_key = ret[1]
                os_status[osName + ip] = worseStatus(os_status[osName + ip], ret[2])
                chassis_status[ip] = worseStatus(chassis_status[ip], os_status[osName + ip])
                test_result_status = worseStatus(test_result_status, chassis_status[ip])
                
                # Add OS object
                if '"pk": ' + str(os_key[osName + ip]) + ',' not in all_os_objects:
                    all_os_objects += '{"model": "rsinterface.os", "pk": ' + str(os_key[osName + ip]) + ', "fields": {\n' + \
                    '    "chassis": ' + str(chassis_key[ip]) + ',\n    "operatingSystem": "' + osName + \
                    '",\n    "status": "' + os_status[osName + ip] + '"}}'
                else:
                    all_os_objects = replaceField(all_os_objects, os_key[osName + ip], "status", os_status[osName + ip])

                if chassis_name[ip] == '':
                    chassis_name[ip] = ret[3]

                # Write to result file that it is in the database
                with open(filepath, 'a') as data_file:
                    # NOTE: consider removing this. We probably don't want to invalidate the JSON, since the website already prevents
                    #       duplicate entries.
                    data_file.write('\nFile in database')
    else:
        # NOTE: This line is a translation of something from the old code.
        # It has since been commented out because it would erase all the other tags, and it might not be necessary.
        # config['tags'] = "--hardwareonly"
        pass

    #Add Chassis object for each chassis
    allChassisObjects = ''
    for idx, ip in enumerate(all_chassis):
        fullIP = "192.168." + ip.replace('_', '.')
        allChassisObjects += '{"model": "rsinterface.chassis", "pk": ' + str(chassis_key[ip]) + \
        ', "fields": {\n    "chassisName": "' + chassis_name[ip] + \
        '",\n    "ipNum": "' + str(fullIP) + '",\n    "status": "' + chassis_status[ip] + '"}},\n'

    # sneak in the tags as the status
    newDateObject = '{"model": "rsinterface.date", "pk": ' + str(date_key) + \
    ', "fields": {\n    "date": "' + stringdate + '",\n    "status": "' + config['tags'] + \
    '" }} ]'
    closingBracket = json_data_combined.rfind(']')
    json_data_combined = json_data_combined[:closingBracket] + all_os_objects + allChassisObjects + newDateObject

    #Formatting for multiple test sequences
    json_data_combined = json_data_combined.replace('][', '').replace('}{', '},\n{').replace(', {', ',\n{').replace(',  {', ',\n{').replace('}\n{', '},\n{')

    #Writes the data to the output file
    with open(outputfile, 'w') as json_file:
        json_file.truncate()
        json_file.write(json_data_combined)


def getField(data, idx):
    return data[data.find(':', idx) + 1: data.find(',', data.find(':', idx) + 1)].split()[0]


def getOSName(osPK, data):
    lookFrom = 0
    osLocation = 0
    while osLocation != -1:
        osLocation = data.find('rsinterface.os', lookFrom)
        lookFrom = osLocation + len('rsinterface.os')

        pkIdx = data.find('pk', lookFrom)

        osNameIdx = data.find('operatingSystem', lookFrom)
        osName = getField(data, osNameIdx).replace('"', '')

        return osName


#Helper function for addModels
#Replaces primary key value that corrosponds with passed fieldName
#Used for incrementing primary key values that build relationships
#
# modelData         - String, the model to be modified
# fieldName         - String, the name of object that this model has a relation to
# highestKey        - Int, the current highest primary key value
def changeFieldPK(modelData, fieldName, highestKey):
    fieldPK = '"' + fieldName + '": '
    pkStart = modelData.find(fieldPK)
    if pkStart != -1:
        pkEnd = modelData.find(',', pkStart)
        pk = modelData[pkStart + len(fieldName) + 4:pkEnd]
        #Increments test primary key
        modelData = modelData.replace(fieldPK + pk, fieldPK + str(int(pk) + highestKey))
    else:
        log.LOG_LVL_3.error('JSON may be malformed')
    return [modelData, int(pk) + highestKey]


# Pulls models from test output file, reassigns primary keys, and adds
# new objects as needed
#
# fileData          - String, the test output file data
# prevHighestKey    - Int, current value of the highest primary key
# chassisKey        - Int, value of chassis primary key to be assisgned
#                       also used for OS object to create child-parent relationship
# osKey             - Int, value of the OS primary key, also used for test to create
#                       child-parent relationship
# osName            - String, name of the OS the test was run on
# dateKey           - Int, primary key for Date object
#
# RETURNS:
# [models, todayStatus, prevHighestKey]
# models            - String, the modified file data
# prevHighestKey    - Int, updated highest key value
# osStatus          - String, worst status of results within fileData
# chassisName       - String, name of Chassis object within fileData
def addModels(
    fileData,
    prevHighestKey,
    osKey,
    osName,
    test_status_dict: dict = constants.TEST_STATUS_DICT
):
    possible_test_statuses = sum([v for v in test_status_dict.values()], [])
    models = '['
    osStatus = test_status_dict['skipped_status'][0]
    testStatus = dict()

    #Replace returns with new lines. Used \r in TestRunner as using \n in the
    #single test output file resulted in two whitespace lines when reading
    #the file back in.
    fileData = fileData.replace('\r', '\n')

    #Highest key in the current test sequence
    highestKey = 0

    #Finds the chassis name if this file has one
    chassisObject = 'rsinterface.chassis'
    hasChassis = fileData.find(chassisObject)
    chassisName = ''
    if hasChassis != -1:
        start = 'chassisName": '
        chassisNameStart = fileData.find(start, hasChassis)
        chassisNameEnd = fileData.find(',', chassisNameStart)
        chassisName = fileData[chassisNameStart + len(start) + 1:chassisNameEnd - 1]

    #Loops for each model object in fileData
    while True:

        #Creates substring of Model object using startModel and endModel
        startModel = fileData.find('{')

        #If a model does not exist, break
        if startModel == -1:
            break
        endModel = fileData.find('}}')
        nextModel = fileData[startModel:endModel + 4]

        #Checks if the object is a chassis
        isChassis = nextModel.find(chassisObject)

        #Chassis creation/modification has been moved to toDatabase
        if isChassis != -1:
            #Ignore chassis, Chassis will be created in toDatabase with correct
            #primary key and fields
            pass

        #Reassign primary key and manipulate data as needed for different objects
        else:
            testPK = None
        
            if '}} ]' in nextModel:
                nextModel = nextModel.replace('}} ]', '}}')
            #Checks if primary key is within the model
            pkLoc = nextModel.find('"pk": ')
            if pkLoc == -1:
                break

            #The position following '"pk": ' in the JSON
            pkLoc += 6

            #Gets the comma following the primary key
            comma = nextModel.find(',', pkLoc)

            #Pulls the value of the primary key
            prevPK = nextModel[pkLoc:comma]

            #Compared this primary key against the largest value of a primary key in
            #this test sequence
            if int(prevPK) > highestKey:
                highestKey = int(prevPK)

            #Handles extra fields if this model is a test
            if nextModel.find('rsinterface.test') != -1:
                #Assign OS field to test
                nextModel = nextModel.replace('"fields": {\n', '"fields": {\n    "os": ' + str(osKey) + ',\n')
                
                pkStart = nextModel.find('"pk":', nextModel.find('rsinterface.test'))
                if pkStart != -1:
                    pkEnd = nextModel.find(',', pkStart)
                    pk = nextModel[pkStart + len('"pk":'):pkEnd]
                    testPK = int(pk) + prevHighestKey

                    testStatusStart = nextModel.find('"status":', pkEnd)
                    if testStatusStart == -1:
                        thisTestStatus = test_status_dict['skipped_status'][0]
                    else:
                        testStatusEnd = nextModel.find('}}', testStatusStart)
                        thisTestStatus = nextModel[testStatusStart + len('"status":') + 2:testStatusEnd - 1]
                        thisTestStatus.replace('"', '')

                    if testPK not in testStatus:
                        testStatus[testPK] = thisTestStatus

                    osStatus = worseStatus(osStatus, testStatus[testPK])

            #Handles extra fields if this model is a log
            elif nextModel.find('rsinterface.log') != -1:
                ret = changeFieldPK(nextModel, 'test', prevHighestKey)
                nextModel = ret[0]
                testPK = ret[1]

                if testPK not in testStatus:
                    testStatus[testPK] = test_status_dict['skipped_status'][0]

                # Update test status
                for status in list(reversed(possible_test_statuses)):
                    if nextModel.find(status) != -1:
                        testStatus[testPK] = worseStatus(testStatus[testPK], status)
                        break

                # Update osStatus based on this log
                osStatus = worseStatus(osStatus, testStatus[testPK])

            #Handles extra fields if this model is a message
            elif nextModel.find('rsinterface.message') != -1:
                nextModel = changeFieldPK(nextModel, 'log', prevHighestKey)[0]
                testPK = nextModel[0]

            #Handles metadata cases
            elif nextModel.find('rsinterface.cpu') != -1 or nextModel.find('rsinterface.dut') != -1:
                nextModel = changeFieldPK(nextModel, 'test', prevHighestKey)[0]
                testPK = nextModel[0]

            #Assigns primary key to this model object
            pk = int(prevPK) + prevHighestKey

            #Update primary key
            nextModel = nextModel.replace('"pk": ' + prevPK + ',', '"pk": ' + str(pk) + ',')

            #Adds the model data to models
            models += nextModel
        #Gets a substring of fileData following the previous model
        fileData = fileData[endModel + 4:]

            
    for key, value in testStatus.items():
        if value not in test_status_dict['pass_status']:
            models = replaceField(models, key, 'status', value)
            testName = getTestName(models, key)

            # HZ: This is probably a very unnecessary feature, and can most likely be removed
            with open('errorFile.csv', 'a') as errorFile:
                error_writer = csv.writer(errorFile, delimiter=str(','))
                error_writer.writerow([osName, testName])

    models += ']'
    #Gets the new highest key based on how many models were added
    prevHighestKey += highestKey

    #Returns the model data, an updated status, the new highest key, chassis status and name
    return [models, prevHighestKey, osStatus, chassisName]

#Finds object with unique primary key pk and replaces the value associated with
#fieldName with newFieldValue
def replaceField(modelData, pk, fieldName, newFieldValue):
    start = modelData.find('"pk": ' + str(pk) + ',')
    oldFieldStart = modelData.find(fieldName + '": ', start)
    oldFieldStart += len(fieldName) + 2
    oldFieldEnd = modelData.find(',', oldFieldStart)
    otherEnd = modelData.find('}', oldFieldStart)
    if (otherEnd != -1 and otherEnd < oldFieldEnd) or oldFieldEnd == -1:
        oldFieldEnd = otherEnd
    return modelData[:oldFieldStart] + '"' + newFieldValue + '"' + modelData[oldFieldEnd:]

def getTestName(modelData, testPK):
    string = '"testName": '
    testData = modelData.find('"pk": ' + str(testPK) + ',')
    testNameStart = modelData.find(string, testData + len(string))
    testNameEnd = modelData.find(',', testNameStart)
    return modelData[testNameStart + len(string) + 1:testNameEnd - 1]


#Gets the files in a directory, checks if a file is in the database, and
#gets the IP associated with a file. Will remove invalid JSON files from the
#returned file list
#
#  - directory      - String, directory with files to be added to database
#
# RETURNS
#   [files, inDB, ip]
#   - files     - list of strings, each file in the directory
#   - inDB      - dictionary, {file : Boolean}, True if file is already in database, False otherwise
#   - ip        - list of strings, IP associated with each file
def getFilesAndIP(directory):
    # log.info("DB - In getFilesAndIP()")
    try:
        files = os.listdir(directory)
    except WindowsError as e:
        # log.info("DB - Missing result directory: " + directory)
        return [[], dict(), []]
    remove = []
    inDB = dict()
    ip = []

    # Checks each file to see that it has an IP, is a JSON, and is not
    # in the database
    for file in files:
        try:
            with open(os.path.join(directory, file), 'r') as curFile:
                fileData = curFile.read()
                if fileData.find('File in database') != -1:
                    remove.append(file)
                    continue
            inDB[file] = False
            fileIP = getIP(file)

            if fileIP != -1:
                ip.append(fileIP)
            else:
                pass
                log.LOG_LVL_1.error('Invalid file name: ' + file + '\n, adding with IP -1')
        except ValueError as e:
            log.LOG_LVL_1.exception('DB - ' + str(file) + ' is an invalid JSON')
            log.LOG_LVL_1.exception('DB - ' + str(e))
            remove.append(file)
    for f in remove:
        files.remove(f)
    return [files, inDB, ip]

#Given a fileName, returns the IP in the name
#Format for results files is currently: dnx_test_result_OSNAME_ip_101_X.json (where X is a number)
#
# - fileName    - String, name of file
# RETURN
# - ip          - String, IP number. In example above this would be 101_X 
def getIP(fileName):
    '''
    TODO: This is bad, since it relies on the filename to extract the IP.
    Instead, note that in a successfully generated json result file, there
    will be a section that has an "ipNum" that we should use instead

    Adding this feature into regression_modules.testrunner_file.UeiResultJSONParser
    might be a good approach, maybe add in a getIP field (this is fine since our
    system assumes that each JSON corresponds to a single ip address)
    '''
    start = fileName.find('test_')
    ext = fileName.find('.json')
    ip = -1
    if start != -1 and ext != -1:
        ip = fileName[start + 5:ext - 7]

    return ip

#Returns the worse case of passed status
#This function could be cleaned up a little to have fewer checks against possibleStatus
def worseStatus(
    statOne,
    statTwo,
    test_status_dict: dict = constants.TEST_STATUS_DICT
):
    # This ordering of statuses is an unfortunate byproduct of the way the former low level regression code
    # handled status "priority".
    possible_test_statuses = test_status_dict['skipped_status'] +\
        test_status_dict['off_status'] + test_status_dict['wrong_os_status'] + test_status_dict['pass_status'] +\
        test_status_dict['neutral_status'] + test_status_dict['error_status']
    
    if statOne not in possible_test_statuses and statTwo not in possible_test_statuses:
        raise LookupError('Both are invalid status: ' + statOne + ' ' + statTwo)
    elif statOne not in possible_test_statuses:
        return statTwo
    elif statTwo not in possible_test_statuses:
        return statOne
    idxOne = possible_test_statuses.index(statOne)
    idxTwo = possible_test_statuses.index(statTwo)
    return statOne if idxOne > idxTwo else statTwo
