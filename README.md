# UEI Low Level Regression Testing

Modified source code for the UEI Low Level Regression Testing process, AKA "ReleaseTest" <br>

This code is a modified version of the Low Level Regression Testing source code that was in use at UEI (United Electronic Industries) after my 6-month long co-op term there. My co-op term was from January to June, and a complete refactor of their testing system was a side project I chose to adopt in March. 

Certain elements of this code have been removed / modified for UEI to allow this code to be uploaded to GitHub.

## Summary

ReleaseTest is the python program used to run the low level regression testing process.
This process works by starting up a clean VM in a certain OS, installing the UEI software suite onto said VM, and then using the UEI TestRunner to run tests on all of the boards in the regression room. This helps ensure that both the software and the hardware can function successfully from a fresh install, mimicking what a customer would experience.

## Built With

This project was developed using Python 3.8.19

All the libraries in this project are fairly standard, with one exception being the VirtualBox API.

### The VirtualBox API

This API is used in `vbox.py`, which is located in the regression_modules directory. You can import it into your python project by using `import vboxapi` after you complete the setup process.

Here are some important Virtual Box resources you can use:
- [website home page](https://www.virtualbox.org/wiki/VirtualBox)
- [downloads page](https://www.virtualbox.org/wiki/Downloads)
- [technical documentation page](https://www.virtualbox.org/wiki/Technical_documentation)
- [SDK programming guide (pdf)](https://download.virtualbox.org/virtualbox/SDKRef.pdf)

In order to get the API working in your project, follow these steps:
1. Download the VirtualBox SDK. This can be found in their downloads page
2. Navigate to the SDK programming guide, and locate where the python setup instructions are (you should be able to find it under section 2.3.2.1)
3. Follow the instructions to set up the library, while heeding the following warning:

***Be warned: as of June 2024, there is a critical error that exists in the vbox SDK***<br>
When you first install the SDK from the downloads page, navigate to `__init__.py` inside of the sdk/installer/vboxapi directory.

Inside of the `VirtualBoxManager.__init__()` function, you will find a line (somewhere near line 1029) that reads: <br>
`vbox = self.platform.getVirtualBox()`
<br>

**This line must be modified to:**<br>
`self.vbox = self.platform.getVirtualBox()`
<br>

If this modification is not done, the VirtualBox API will not function at all!


## TODO

Here is a "TODO" list for developers, categorized by priority level:

...