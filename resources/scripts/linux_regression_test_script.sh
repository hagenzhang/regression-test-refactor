#!/bin/bash

# Syntax: win_regression_test_script.sh
# Argument %1: <test sequence name>.xml
# Argument %2: <test result name>.json
# Argument %3: <test runner log name>.txt
# Argument %4: -b (optional, run power layer tests only)

echo "[$(date)] -            Test started"

TESTSUITE_DIR=uei_dnx_regression_suite_1.0_linux

# test for directory
if [[ ! -d "${TESTSUITE_DIR}" || -L "${TESTSUITE_DIR}" ]] ; then
    echo "{ \"Error\": \"could not find ~/${TESTSUITE_DIR}/ directory; edit Linux_regression_test_script.sh to make this JSON useful.\" }"
    echo "Fatal Error: could not find TESTSUITE directory: ${TESTSUITE_DIR}"
    exit 1
elif [[ ! -e "${TESTSUITE_DIR}/DNxTestSuite.so" || ! -e "${TESTSUITE_DIR}/ueitestrunner" ]] ; then
    echo "{ \"Error\": \"could not find ~/${TESTSUITE_DIR}/ 'DNxTestSuite.so' or 'ueitestrunner'; edit Linux_regression_test_script.sh to make this JSON useful.\" }"
    echo "Fatal Error: could not find 'DNxTestSuite.so' and 'ueitestrunner' in: ${TESTSUITE_DIR}"
    exit 1
fi

# replace testsuite name with DNxTestSuite.so
# this is done in order to prevent the testrunner from reporting a diff due to inconsistent metadata.
echo "[$(date)] Replacing testsuite name in $1"
sed -i 's#DNxTestSuiteVC9D\.dll#\./DNxTestSuite\.so#' $1


# copy XML to the test directory
cp $1 $TESTSUITE_DIR

# execute
pushd $TESTSUITE_DIR

echo "[$(date)] - Executing Regression Test: $1"

if [[ $4 == "-b" ]]; then
    echo Running Power Layer Tests Only!
    ./ueitestrunner -b -s ./DNxTestSuite.so -g -x $1 -o $2 > $3 2>&1
else
    echo Running All Available Tests!
    ./ueitestrunner -s ./DNxTestSuite.so -g -x $1 -o $2 > $3 2>&1
fi

if [[ $? == 139 ]]; then
    if [[ -e "/usr/bin/gdb" || -e "/usr/bin/valgrind" ]]; then
        if [[ -e "/usr/bin/gdb" ]]; then
            echo "[$(date)] Step: segfaulted so trying gdb (without core file)"
            gdb -q -ex="set confirm off" -ex=r -ex=bt -ex=q --args ./ueitestrunnerD -x $1 -o $2
            echo $?
        fi
        if [[ -e "/usr/bin/valgrind" ]]; then
            echo "[$(date)] Step: segfaulted so trying valgrind for more info"
            /usr/bin/valgrind -v --tool=memcheck --leak-check=yes --leak-check=full --show-reachable=yes --track-origins=yes ./ueitestrunnerD -x $1 -o $2
            echo $?
        fi
    else
        echo "\"Error\": \"segfault during ./ueitestrunner call, attempting slower ./ueitestrunnerD\" }"
    fi
fi

popd

#copy XML, results, and logs back to the home directory
cp $TESTSUITE_DIR/$1 .
cp $TESTSUITE_DIR/$2 .
cp $TESTSUITE_DIR/$3 .

# adding the old testsuite name back
echo re-replacing the testsuite name from DNxTestSuite.so back to DNxTestSuiteVC9D.dll
sed -i 's#\./DNxTestSuite\.so#DNxTestSuiteVC9D\.dll#' $1

echo "[$(date)] -            Finished test"
