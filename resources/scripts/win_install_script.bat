@echo off
setlocal enableDelayedExpansion
setlocal enableExtensions

REM COMMAND FORMAT: ./scriptname BUILD LOGFILE.txt -s
REM                  ^ arg0      ^arg1  ^args2     ^optional arg3

REM The way handle checking for install errors (as opposed to generic script errors) that we use
REM is centered around the boolean. If we are ever exiting due to an install error or while the 
REM install_error = true, then we should exit with a return code of 5. This communicates to the 
REM python code that there was an install error from building, not some random error that occured.

REM A return code of 5 will add a script error tag to the website as well, and prompt the dev
REM to look at the logfile to discover what went wrong.
REM We use a logfile instead of using stdout/stderr so we have more control over what we log.

REM ==============================================================================
set LOG="%cd%\%2"
echo ===== Batch Install Script Started with Args: %* ===== >> %LOG%

REM ==============================================================================

REM Practical bitness test
set BITNESS=32
if exist "C:\Progra~2" set BITNESS=64

echo [!DATE!_!TIME!][!BITNESS!-bit] === Installing Software Suite via MSI === >> %LOG%

REM ==========================================================================================

REM Installing the windows MSI
echo PowerDNA Software Suite installer started at: !DATE!_!TIME! >> %LOG%
msiexec /i d:\pdna!BITNESS!.msi /qb! /log win_msi.log REBOOT="ReallySuppress" 2> err.txt
if not %errorlevel% == 0 (
    echo INSTALLSCRIPTERROR: PowerDNA Software Suite installer errored out at: !DATE!_!TIME! >> %LOG%
    type err.txt >> %LOG%
    exit 5
)

echo PowerDNA Software Suite installer finished at: !DATE!_!TIME! >> %LOG%
echo === Installer Software Suite Completed === >> %LOG%

echo Sleeping for 5 seconds... >> %LOG%
ping localhost -n 5 -w 1000 > NUL

set PDNABIN="C:\Progra~1\UEI\PowerDNA\SDK\Bin"
if !BITNESS! EQU 64 set PDNABIN="C:\Progra~2\UEI\PowerDNA\SDK\Bin"

echo TestRunner located at %PDNABIN% >> %LOG%

REM ==========================================================================================

if not "%3" == "-s" (
    echo [!DATE!_!TIME!][!BITNESS!-bit] === Skipping Sample Building === >> %LOG%
    exit 0
)
echo [!DATE!_!TIME!][!BITNESS!-bit] === Starting Sample Building === >> %LOG% 

:SET_PATH
REM Set paths depending on architecture - 64 bit paths are already in VM env variables
if !BITNESS! EQU 32 set PATH=%PATH%;"C:\Progra~1\Microsoft Visual Studio\Common\MSDev98\Bin"; ^
"C:\Progra~1\Microsoft Visual Studio 9.0\Common7\IDE";"C:\Progra~1\Microsoft Visual Studio 9.0\VC\vcpackages"
if !BITNESS! EQU 32 set PDNAROOT="C:\Progra~1\UEI\PowerDNA\SDK"
if !BITNESS! EQU 32 set UEIDAQROOT="C:\Progra~1\UEI\Framework"

REM ==========================================================================================     PDNA C++

echo [!DATE!_!TIME!][!BITNESS!-bit] === Building C Examples === >> %LOG%

set TAG_FLAG="false"
cd "%PDNAROOT%\Examples\Visual C++"

echo Upgrading Visual C++ Projects >> %LOG%
for /R %%i in (*.vcproj) do call:UPGRADE_DSP "%%i"

echo Rebuilding Visual C++ Projects >> %LOG%
for /R %%i in (*.vcproj) do call:REBUILD_PROJ "%%i"

REM ==========================================================================================     AnsiC

echo [!DATE!_!TIME!][!BITNESS!-bit] === Building ANSI C Examples === >> %LOG%

cd "%UEIDAQROOT%\CPP\examples_ansiC"
echo Upgrading AnsiC Projects >> %LOG%
devenv examples_ansiC.sln /upgrade 2> err.txt
if not %errorlevel% == 0 (
    echo Error after upgrading AnsiC >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

echo Rebuilding AnsiC Debug >> %LOG%
devenv examples_ansiC.sln /rebuild Debug 2> err.txt
if not %errorlevel% == 0 (
    echo Error after rebuilding AnsiC Debug >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

echo Rebuilding AnsiC Release >> %LOG%
devenv examples_ansiC.sln /rebuild Release 2> err.txt
if not %errorlevel% == 0 (
    echo Error after rebuilding AnsiC Release >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

REM ==========================================================================================     Framework C++

echo [!DATE!_!TIME!][!BITNESS!-bit] === Building C++ Examples === >> %LOG%

cd "%UEIDAQROOT%\CPP\examples"
echo Upgrading Framework C++ Projects >> %LOG%
devenv examples.sln /upgrade 2> err.txt
if not %errorlevel% == 0 (
    echo Error after upgrading Framework Projects >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

echo Rebuilding Framework C++ Debug >> %LOG%
devenv examples.sln /rebuild Debug 2> err.txt
if not %errorlevel% == 0 (
    echo Error after rebuilding Framework C++ Debug >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

echo Rebuilding Framework C++ Release >> %LOG%
devenv examples.sln /rebuild Release 2> err.txt
if not %errorlevel% == 0 (
    echo Error after rebuilding Framework C++ Release >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

REM ==========================================================================================     DotNet C#

echo [!DATE!_!TIME!][!BITNESS!-bit] === Building .NET C# Examples === >> %LOG%

cd "%UEIDAQROOT%\Dotnet\examples"
echo Upgrading C# Projects >> %LOG%
devenv examples.sln /upgrade 2> err.txt
if not %errorlevel% == 0 (
    echo Error after upgrading C# Projects >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

echo Retargeting C# Projects >> %LOG%
for /R %%i in (*.csproj) do call:RETARGET_CSPROJ "%%i"

echo Rebuilding C# Debug >> %LOG%
devenv examples.sln /rebuild Debug 2> err.txt
if not %errorlevel% == 0 (
    echo Error after rebuilding C# Debug >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

echo Rebuilding C# Release >> %LOG%
devenv examples.sln /rebuild Release 2> err.txt
if not %errorlevel% == 0 (
    echo Error after rebuilding C# Release >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

REM ==========================================================================================     DotNet Visual Basic

echo [!DATE!_!TIME!][!BITNESS!-bit] === Building VB Examples === >> %LOG%

cd "%UEIDAQROOT%\Dotnet\vb_examples"
echo Upgrading Visual Basic Projects >> %LOG%
devenv vb_examples.sln /upgrade 2> err.txt
if not %errorlevel% == 0 (
    echo Error after upgrading Visual Basic Projects >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

echo Retargeting Visual Basic Projects >> %LOG%
for /R %%i in (*.vbproj) do call:RETARGET_CSPROJ "%%i"

echo Rebuilding Visual Basic Debug >> %LOG%
devenv vb_examples.sln /rebuild Debug 2> err.txt
if not %errorlevel% == 0 (
    echo Error after rebuilding Visual Basic Debug >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

echo Rebuilding Visual Basic Release >> %LOG%
devenv vb_examples.sln /rebuild Release 2> err.txt
if not %errorlevel% == 0 (
    echo Error after rebuilding Visual Basic Release >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)

REM ==========================================================================================     UeiDaq Python

REM py -m pip install "%UEIDAQROOT%\Python\UeiDaq-5.3.0-cp38-cp38-win_amd64.whl" 
REM NOTE: something is broken here, this file does not exist in the windows 10 VM

REM ==========================================================================================

goto :END

REM ==========================================================================================

:REBUILD_PROJ
@echo off
setlocal enableDelayedExpansion
setlocal enableExtensions
devenv "%~1" /rebuild 2> err.txt
if not %errorlevel% == 0 (
    echo Error rebuilding project: "%~1" >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)
goto:EOF

REM ==========================================================================================

:UPGRADE_DSP
echo off
vcbuild /upgrade "%~1" 2> err.txt
if not %errorlevel% == 0 (
    echo Error upgrading project: "%~1" >> %LOG%
    type err.txt >> %LOG%
    set TAG_FLAG="true"
)
goto:EOF

REM ==========================================================================================

:RETARGET_CSPROJ
REM manually edit the UEI SDK version

echo off
set inputfile="%~1"
set tempfile=%random%-%random%.tmp

copy /y nul %tempfile%

REM Handles the two formats of vbproj found in the VB examples
for /F "usebackq tokens=*" %%A in (%inputfile%) do (
    set __CURRENT_LINE=%%A
    if not "!__CURRENT_LINE:HintPath=!" == "!__CURRENT_LINE!" (
        if not "!__CURRENT_LINE:<=!" == "!__CURRENT_LINE!" (
            echo ^<HintPath^>..\..\DotNet2\UeiDaqDNet.dll^</HintPath^> >>%tempfile%
        ) else (
           echo HintPath = "..\..\DotNet2\UeiDaqDNet.dll">>%tempfile%
        )
    ) else (
        echo %%A >> %tempfile%
    )
)

copy /y %tempfile% %inputfile%
del %tempfile%
endlocal

goto:EOF

REM ==========================================================================================

:END
echo ===== Batch Install Script Finished at !DATE!_!TIME! ===== >> %LOG%
if !TAG_FLAG! == "true" (
    echo Sample Building Errors Detected... Exiting with Error Code 5 >> %LOG%
    echo INSTALLSCRIPTERROR >> %LOG%
    exit /b 5
)
exit /b 0

