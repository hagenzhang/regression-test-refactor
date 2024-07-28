@REM Syntax: win_regression_test_script.bat
@REM Argument %1: <test sequence name>.xml
@REM Argument %2: <test result name>.json
@REM Argument %3: <test runner log name>.txt
@REM Argument %4: -b (optional, run power layer tests only)
@echo off
echo invoking win_regression_test_script with arguments %* in PDNAROOT\bin
setlocal enableDelayedExpansion



@REM Practical bitness test
@set BITNESS=32
@if exist "C:\Progra~2" set BITNESS=64

@REM ==========================================================================================

@REM Sets path variables depending on bitness
REM WIN32
set PDNAROOT="C:\Progra~1\UEI\PowerDNA\SDK"
set PDNABIN="C:\Progra~1\UEI\PowerDNA\SDK\Bin"
set UEIDAQROOT="C:\Progra~1\UEI\Framework"

REM WIN64
if !BITNESS! EQU 64 set PDNAROOT="C:\Progra~2\UEI\PowerDNA\SDK"
if !BITNESS! EQU 64 set PDNABIN="C:\Progra~2\UEI\PowerDNA\SDK\Bin"
if !BITNESS! EQU 64 set UEIDAQROOT="C:\Progra~2\UEI\Framework"

@REM ==========================================================================================

@REM Moves the sequence XML to the test runner directory
@echo [!DATE!_!TIME!][!BITNESS!-bit] test is %PDNABIN%\UeiTestRunnerVC9D.exe -x %1 -o %2
echo off
copy %1 "%PDNABIN%\"
@if %ERRORLEVEL% NEQ 0 echo Fatal Error: Could not copy %1 to %PDNABIN%
@if %ERRORLEVEL% NEQ 0 goto CREATE_EMPTY_JSON

@REM ==========================================================================================
@REM Goes to test runner directory and executes it for the given test sequence
pushd "%PDNABIN%"
@echo [!DATE!_!TIME!] - Performing test sequence:

if "%4" == "-b" (
    echo Set to run power layer test only
    @echo [!DATE!_!TIME!][!BITNESS!-bit] test is %PDNABIN%\UeiTestRunnerVC9D.exe -g -b -s DNxTestSuiteVC9D.dll -x %1 -o %2
    .\UeiTestRunnerVC9D.exe -b -s DNxTestSuiteVC9D.dll -g -x %1 -o %2 > %3 2>&1

    @REM Use this command instead to only generate XMLs, but not run any tests
    @REM .\UeiTestRunnerVC9D.exe -g -b -x %1 > %3

) else (
    echo Set to run all available tests
    @echo [!DATE!_!TIME!][!BITNESS!-bit] test is %PDNABIN%\UeiTestRunnerVC9D.exe -g -s DNxTestSuiteVC9D.dll -x %1 -o %2
    .\UeiTestRunnerVC9D.exe -s DNxTestSuiteVC9D.dll -g -x %1 -o %2 > %3 2>&1
    
    @REM Use this command instead to only generate XMLs, but not run any tests
    @REM .\UeiTestRunnerVC9D.exe -g -x %1 > %3
)

@echo [!DATE!_!TIME!] -                Test sequence complete
@echo: 
@if %ERRORLEVEL% neq 0 echo UeiTestRunnerVC9D.exe -x %1 -o %2 error %ERRORLEVEL% returned
@REM @7za a -tzip %3.zip *.xml *.json *.out *.txt
del *.out
popd

@REM ==========================================================================================

@REM Moves the new XML, the test result json, and the testrunner logs
move "%PDNABIN%\%1" .
move "%PDNABIN%\%2" .
move "%PDNABIN%\%3" .

exit /b 0

@REM ==========================================================================================


