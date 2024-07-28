#!/bin/bash

# COMMAND FORMAT: ./scriptname BUILD LOGFILE.txt -s
#                  ^ arg0      ^arg1  ^args2     ^optional arg3

# The way handle checking for install errors (as opposed to generic script errors) that we use
# is centered around the boolean. If we are ever exiting due to an install error or while the 
# install_error = true, then we should exit with a return code of 5. This communicates to the 
# python code that there was an install error from building, not some random error that occured.

# A return code of 5 will add a script error tag to the website as well, and prompt the dev
# to look at the logfile to discover what went wrong.
# We use a logfile instead of using stdout/stderr so we have more control over what we log.

# ==============================================================================
LOG=/home/tester/$2

# ==============================================================================

echo "===== Bash Install Script Started with Args: $0 $@ =====" >> $LOG

# ==============================================================================
# Locating the ISO image
echo "[$(date)] === Installing Software Suite ===" >> $LOG

echo "Locating the Mounted ISO Image..." >> $LOG 
RELEASE_LOCATION=/run/media/tester/CDROM/Linux
if [[ ! -d "$RELEASE_LOCATION" ]]; then
	RELEASE_LOCATION=/media/CDROM/Linux
	if [[ ! -d "$RELEASE_LOCATION" ]]; then
		sudo mount -r /dev/cdrom/media/CDROM
		RELEASE_LOCATION=/dev/cdrom/media/CDROM/Linux
		if [[ ! -d "$RELEASE_LOCATION" ]]; then
			echo "INSTALLSCRIPTERROR: Failed to access Release location in VM" >> $LOG
			exit 5
		fi
	fi
fi
echo "ISO located at: $RELEASE_LOCATION" >> $LOG

# ==============================================================================
# unzipping the software suite tarbal

echo "Locating Software Suite Tarbal..." >> $LOG
RELEASE_TAR_BALL=`ls $RELEASE_LOCATION/PowerDNA*`
cd "$RELEASE_LOCATION"
# manually assign the file path in case it doesnt work from the ls command
if [[ ! -f "$RELEASE_TAR_BALL" ]]; then
	cd "$RELEASE_LOCATION"
	echo $PWD
	for f in `ls`; do
		echo "$f"
		if printf '%s' "$f" | grep -Eq '^PowerDNA'; then
			RELEASE_TAR_BALL="$RELEASE_LOCATION"/"$f"
			echo "Manually set ReleaseTarbal: $RELEASE_TAR_BALL"
		fi
	done
fi
echo "Release Tarbal: $RELEASE_TAR_BALL"

cd /home/tester
# strip file extension
RELEASE_VER=`echo ${RELEASE_TAR_BALL%.[^.]*}`

# get string after last '_'
RELEASE_VER=`echo ${RELEASE_VER##*_}`

RDOT1=`echo $RELEASE_VER | cut -d. -f1`
RDOT2=`echo $RELEASE_VER | cut -d. -f2`
RDOT3=`echo $RELEASE_VER | cut -d. -f3`
RDOT4=`echo $RELEASE_VER | cut -d. -f4`

echo "Extracting $RELEASE_TAR_BALL"
tar xvfz $RELEASE_TAR_BALL

SRC_DIR=`echo PowerDNA_Linux_$RDOT1.$RDOT2.$RDOT3/src`
if [[ ! -d "${SRC_DIR}" || -L "${SRC_DIR}" ]] ; then
    echo "INSTALLSCRIPTERROR: could not find PowerDNA directory: ${SRC_DIR}" >> $LOG
    exit 5
fi

# ==============================================================================

echo "=== Software Suite Install Completed ===" >> $LOG

# ==============================================================================
# This section of the script is an addition done for the sake of allowing 
# testing on the UDP SSL ports. Since it does not impact normal behavior, 
# it is safe to leave here.
pushd $SRC_DIR/DAQLib
sed -i '1s/^/DTLS=1\n\n/' Makefile
popd
# ==============================================================================
# Building DAQLib
echo "[$(date)] === Building DAQLib ===" >> $LOG
pushd $SRC_DIR

echo "Running 'make' in $PWD" >> $LOG
make 2> err.txt
if [ $? -ne 0 ]; then
	echo "INSTALLSCRIPTERRORr: 'make' for DAQLib failed"
	cat err.txt >> $LOG
	exit 5
fi

echo "Running 'sudo make install ' in $PWD" >> $LOG
sudo make install 2> err.txt
if [ $? -ne 0 ]; then
	echo "INSTALLSCRIPTERROR: 'sudo make install' for DAQLib failed" >> $LOG
	cat err.txt >> $LOG
	exit 5
fi
popd

# ==============================================================================

echo "=== DAQLib Building Completed ===" >> $LOG

# ==============================================================================
# === Creating the TestRunner executables
echo "[$(date)] === Building TestRunner ===" >> $LOG

TESTSUITE_DIR=/home/tester/uei_dnx_regression_suite_1.0_linux
if [[ "$1" == "5.3" ]]; then
	# Install test suite to be able to run regression tests
	TESTSUITE_TAR_BALL=$RELEASE_LOCATION/uei_dnx_regression_suite_1.0_linux.tgz

	echo "5.3: retrieving regression test suite from tarball" >> $LOG
	tar xvfz $TESTSUITE_TAR_BALL

	cd $TESTSUITE_DIR
	make clean

	echo "Running 'make all' in $PWD" >> $LOG
	make all 2> err.txt
	if [ $? -ne 0 ]; then
		echo "INSTALLSCRIPTERROR: 'make' failed for Regression Test Suite" >> $LOG
		cat err.txt >> $LOG
		exit 5
	fi

	# also compile debug version of testrunner
	make clean
	
	echo "Running 'make all DEBUG=1' in $PWD" >> $LOG
	make all DEBUG=1 2> err.txt
	if [ $? -ne 0 ]; then
		echo "INSTALLSCRIPTERROR: 'make all DEBUG=1' failed for Regression Test Suite" >> $LOG
		cat err.txt >> $LOG
		exit 5
	fi

	cd ..

elif [[ "$1" == "5.2" ]]; then 
	echo "5.2: retrieving regression test suite from SVN" >> $LOG

	svn checkout svn://subversion/Software/PowerDNA/3.3.x/Test\ Suite/ /home/tester/uei_dnx_regression_suite_1.0_linux/TestSuite
	svn checkout svn://subversion/Software/Common/UeiTestRunner/ /home/tester/uei_dnx_regression_suite_1.0_linux/UeiTestRunner
	svn checkout svn://subversion/Software/PowerDNA/3.3.x/UEIPAC/UeiPalLib /home/tester/uei_dnx_regression_suite_1.0_linux/UeiPalLib

	# change and move the makefile
	echo "replacing TestSuite Makefile" >> $LOG
	mv /home/tester/uei_dnx_regression_suite_1.0_linux/TestSuite/Makefile.dist $TESTSUITE_DIR/Makefile

	# make the test suite
	cd $TESTSUITE_DIR
	make clean

	echo "Running 'make all' in $PWD" >> $LOG
	make all 2> err.txt
	if [ $? -ne 0 ]; then
		echo "INSTALLSCRIPTERROR: 'make' failed for Regression Test Suite" >> $LOG
		cat err.txt >> $LOG
		exit 5
	fi

	make clean
	
	echo "Running 'make all DEBUG=1' in $PWD" >> $LOG
	make all DEBUG=1 2> err.txt
	if [ $? -ne 0 ]; then
		echo "INSTALLSCRIPTERROR: 'make all DEBUG=1' failed for Regression Test Suite" >> $LOG
		cat err.txt >> $LOG
		exit 5
	fi
fi
# ==============================================================================

echo "=== TestRunner Building Completed ==="

# ==============================================================================
# === Sample building if the -s flag exists
if [[ "$3" != "-s" ]]; then
    exit 0
fi

# ==============================================================================
# === Sample Building
echo "[$(date)] === Building Samples ==="
TAG_FLAG=false

pushd $SRC_DIR
echo "Running 'make samples' in $PWD" >> $LOG
make samples 2> err.txt
if [ $? -ne 0 ]; then
	echo "Critical Error: 'make samples' failed for DAQLib Samples" >> $LOG
	cat err.txt >> $LOG
	TAG_FLAG=true
fi
popd

# ==============================================================================

echo "=== Sample Building Completed ===" >> $LOG

# ==============================================================================
# === if not in Linux CentOS, quit out
cd /home/tester/
VERSION_ID=$(grep "^ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"')

# We do the end check if we are not in CentOS
if [[ "$VERSION_ID" != "centos" ]]; then
	echo "[$(date)] ===== Install Script Completed =====" >> $LOG
	if [ $TAG_FLAG = 'true' ]; then
		echo "Exiting with return code 5..." >> $LOG
		echo "INSTALLSCRIPTERROR" >> $LOG
		exit 5
	fi
	echo "Exiting with return code 0..." >> $LOG
	exit 0
fi

# ==============================================================================
# === if in Linux Centos, build Framework
echo "[$(date)] === Building Framework ===" >> $LOG

pushd $SRC_DIR

cd Framework
mkdir build
cd build

# install Cmake (necessary to build Framework)
echo "Installing Cmake" >> $LOG
mv /home/tester/cmake-3.6.0.tar.gz .
tar xvzf cmake-3.6.0.tar.gz
cd cmake-3.6.0;./configure

echo "Running 'make' in $PWD" >> $LOG
make 2> err.txt
if [ $? -ne 0 ]; then
	echo "INSTALLSCRIPTERROR: 'make' for Cmake failed" >> $LOG
	cat err.txt >> $LOG
	exit 5
fi

echo "Running 'sudo make install' in $PWD" >> $LOG
sudo make install 2> err.txt
if [ $? -ne 0 ]; then
	echo "INSTALLSCRIPTERROR: 'sudo make install' for Cmake failed" >> $LOG
	cat err.txt >> $LOG
	exit 5
fi

cd ..

# ==========================================================================================
# this little wonky thing is required to make the cmake .. command below run without errors.
# it's modifying the CMakeLists.txt files inside of UeiPDNADriver and UeiSimuDriver to make
# sure that the add_library line is correct. Attempting to access the CMakeLists.txt file 
# using a path didn't work, so I ended up using some cd calls to get to where I needed to be.
# - Hagen Zhang
cd ../Source/UeiPDNADriver
sed -i 's/add_library(${PROJECT_NAME} OBJECT ${ALL_FILES})/add_library(${PROJECT_NAME} SHARED ${ALL_FILES})/g' CMakeLists.txt

cd ../UeiSimuDriver
sed -i 's/add_library(${PROJECT_NAME} OBJECT ${ALL_FILES})/add_library(${PROJECT_NAME} SHARED ${ALL_FILES})/g' CMakeLists.txt
cd ../../build
# ==========================================================================================

echo "Running 'cmake ..' in $PWD" >> $LOG
cmake .. 2> err.txt
if [ $? -ne 0 ]; then
	echo "INSTALLSCRIPTERROR: 'cmake' for Framework failed" >> $LOG
	cat err.txt >> $LOG
	exit 5
fi

echo "Running 'make' in $PWD" >> $LOG
make 2> err.txt
if [ $? -ne 0 ]; then
	echo "INSTALLSCRIPTERROR: 'make' for Framework failed" >> $LOG
	cat err.txt >> $LOG
	exit 5
fi

echo "Running 'sudo make install' in $PWD" >> $LOGs
sudo make install 2> err.txt
if [ $? -ne 0 ]; then
	echo "INSTALLSCRIPTERROR: 'sudo make install' for Framework failed" >> $LOG
	cat err.txt >> $LOG
	exit 5
fi

# ==========================================================================================
# === Building UEIDAQ Python Module for Framework
echo "Building Python Framework" >> $LOG

cd ../Python
chmod +x build.sh
sudo ./build.sh
if [[ "$1" == "5.2" ]]; then
	sudo tar xzvf dist/UeiDaq-5.2.0.linux-x86_64.tar.gz -C /
else
	sudo tar xzvf dist/UeiDaq-5.3.0.linux-x86_64.tar.gz -C /
fi

sudo ldconfig

if [ $? -ne 0 ]; then
	echo "INSTALLSCRIPTERROR: Python Framework install failed" >> $LOG
	TAG_FLAG=true
	exit 5
fi

popd
# ==========================================================================================

echo "=== Framework Build Completed ===" >> $LOG

# ==========================================================================================

# Do the end check to close out
echo "[$(date)] ===== Install Script Completed =====" >> $LOG
if [ $TAG_FLAG = 'true' ]; then
	echo "Exiting with return code 5..." >> $LOG
	echo "INSTALLSCRIPTERROR" >> $LOG
	exit 5
fi
echo "Exiting with return code 0..." >> $LOG
exit 0
