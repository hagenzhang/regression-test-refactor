'''vbox_controller.py

A library for performing basic functions on VirtualBox VMs.
'''

import os
import time
import paramiko
import shutil
import vboxapi


def create_vm_controllers(
    vmanager: vboxapi.VirtualBoxManager,
    vm_name: str
):
    '''Provides all the necessary components to control a VirtualBox VM.

    To instantiate a virtual box manager, simply use:

    import vboxapi
    vmanager: vboxapi.VirtualBoxManager = vboxapi.VirtualBoxManager(None, None)

    NOTE: To ensure proper functionality, only use one instance of a VirtualBoxManager at any given time.
          Instantiating multiple VirtualBoxManager objects will cause bizarre behavior.
    
    Args:
        vmanager (vboxapi.VirtualBoxManager):   VirtualBox Manager object.
        vm_name (str):                          name of the VM inside of VirtualBox.
    Returns:
        vbox:           VirtualBox singleton object.
        vm:             VirtualBox virtual machine.
        vsession:       VirtualBx VM Session.
    '''
    vbox = vmanager.vbox
    vm = vbox.findMachine(vm_name)
    vsession = vmanager.getSessionObject(vbox)
    
    return vbox, vm, vsession



def get_vm_connect_clients(vip: str, vport: int, vm_user: str, vm_pass: str):
    '''Connects to a VM via paramiko and returns the SSH/SFTP clients.

    This function can be used for other devices, but since we're using it solely to
    connect to the VirtualBox VMs, all documentation/references to this function will
    treat it as a tool for doing that one specific task.

    When the code is finished using the ssh and sftp clients, they should be closed 
    using the 'close_vm_connect_clients' function!
    
    Args:
        vip (str):      ipv4 address of the virtual machine you want to connect to.
        vport (int):    port number for the ssh client to use.
        vm_user (str):  username of the device.
        vm_pass (str):  password of the device.
    Returns:
        ssh     (paramiko.SSHClient): paramiko SSH client to the VM.
        sftp    (paramiko.SFTPClient): paramiko SFTP client to the VM.

    '''
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # you might see this freak out when you change VM IPs
    ssh.connect(vip, vport, vm_user, vm_pass)
    sftp = ssh.open_sftp()
    return ssh, sftp



def close_vm_connect_clients(ssh: paramiko.SSHClient, sftp: paramiko.SFTPClient):
    '''Closes the given paramiko SSH/SFTP clients.
    
    This function must be called after the user is done using the clients!

    Args:
        ssh (paramiko.SSHClient):   paramiko SSH client to a VM.
        sftp (paramiko.SFTPClient): paramiko SFTP client to a VM.
    Returns:
        None
    '''
    if ssh:
        ssh.close()
    if sftp:
        sftp.close()



def get_file_from_vm(
    vip: str,
    vport: int,
    vm_user: str,
    vm_pass: str,
    vm_src: str,
    local_dst: str
):
    '''Retrieves a file from the VirtualBox VM with the given information via SFTP Client.

    This function is stronger than just using it for our VMs, but since
    this is the context in which it is used, it will be treated accordingly.

    The base filepath of the VM will be its "home directory", which can vary from
    VM to VM. The VM source should be the VMs home directory. If it isn't, then
    there can be some issues that prevent the file retrieval from happening.

    If the filename of the file you want to retrieve is already used in the current working
    directory of this function call, it will be overwritten!

    TODO: Implement support for file retrieval from anywhere within the VM.
    This will probably require copying the file from the original location
    over to the VM home directory, retrieving the file from the home directory,
    and then deleting the copy.

    If the file does not exist, it will raise an exception, but the desired file will
    be created anyways (it will just be empty.)

    Args:
        vip (str):          ipv4 address of the virtual machine you want to connect to.
        vport (int):        port number for the ssh client to use.
        vm_user (str):      username of the device.
        vm_pass (str):      password of the device.
        vm_src (str):       path to the file to retrieve in the VM.
        local_dst (str):    path to move the file to from the VM.
    Returns:
        local_dst (str):    path to move the file to from the VM.
    '''
    ssh, sftp = get_vm_connect_clients(vip, vport, vm_user, vm_pass)

    try:
        sftp.get(vm_src, os.path.basename(vm_src))
    except FileNotFoundError:
        # Even if the get command fails, it will still create a file. So, we need to move it regardless
        location = shutil.move(os.path.basename(vm_src), local_dst)
        close_vm_connect_clients(ssh, sftp)
        raise
    else:
        location = shutil.move(os.path.basename(vm_src), local_dst)
        close_vm_connect_clients(ssh, sftp)
        return location



def put_file_on_vm(
    vip: str,
    vport: int,
    vm_user: str,
    vm_pass: str,
    local_src: str,
    vm_dst: str
):
    '''Places a file onto the VirtualBox VM with the given information via SFTP Client.

    This function is stronger than just using it for our VMs, but since
    this is the context in which it is used, it will be treated accordingly.

    The base filepath of the VM will be its "home directory", which can vary from
    VM to VM.
    
    Args:
        vip (str):          ipv4 address of the virtual machine you want to connect to.
        vport (int):        port number for the ssh client to use.
        vm_user (str):      username of the device.
        vm_pass (str):      password of the device.
        local_src (str):    path to move the file to from the VM.
        vm_dst (str):       path to move the file to on the VM.
    Returns:
        vm_dst (str):       path to move the file to on the VM.
    '''
    ssh, sftp = get_vm_connect_clients(vip, vport, vm_user, vm_pass)
    sftp.put(local_src, vm_dst)
    close_vm_connect_clients(ssh, sftp)
    return vm_dst



def run_command_ssh(
    ip: str,
    port: int,
    username: str,
    password: str,
    command: str,
    timeout=None
):
    '''Runs the given command to a VM through a ssh client.

    This function can be used for things outside of the VM, but since
    this is the context in which it is used, it will be treated accordingly.
    
    Args:
        ip (str):               IPv4 address of the machine to run the given command on.
        port (int):             port number to use.
        username (str):         username of the machine.
        password (str):         password of the machine.
        command (str):          full command to run
        timeout (int | None):   timeout to use for the command. None if no timeout is desired
    Returns:
        script_output (str):    decoded stdout from the command.
        script_error (str):     decoded stderr from the command.
        exit_status (int):      exit status code of the command.
    '''
    ssh_client, sftp_client = get_vm_connect_clients(ip, port, username, password)
    script_output, script_error, exit_status = ('', '', -1) # assigning default values
    
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
        script_output = stdout.read().decode("utf-8")
        script_error = stderr.read().decode("utf-8")
        exit_status = stdout.channel.recv_exit_status()

        stdin.close()
        stdout.close()
        stderr.close()
        
    except:
        close_vm_connect_clients(ssh_client, sftp_client)
        raise
    else:
        close_vm_connect_clients(ssh_client, sftp_client)
        return script_output, script_error, exit_status


def start_vm(
    vname: str,
    vmanager: vboxapi.VirtualBoxManager, 
    vbox,
    vm,
    vsession,
    snapshot:str='',
):
    '''Starts the VM associated with the given VM controllers/information.
    
    If a snapshot is provided, it will use the snapshot.
    Else, boot to the current state of the VM.
    
    If the VM is already online when this function is called, it will
    only reboot the VM if a snapshot is specified (in which case it will
    proceed to boot to the specified VM snapshot). 
    Else, just keep the current VM alive.
    
    Args:
        vname (str):                    name of the VirtualBox VM to open.
        vmanager (VirtualBoxManager):   VirtualBox Manager object.
        vbox:                           VirtualBox singleton object.
        vsession:                       VirtualBx VM Session.
        vm:                             VirtualBox virtual machine
        snapshot:                       name of the snapshot to boot the VM into.
    Returns:
        None
    '''
    # If the VM is already running, check if the function called specified a snapshot
    # If snapshot != '', then close down the VM to reboot it to the snapshot
    # Else, just skip this function and leave the VM running
    if vm_is_running(vmanager, vm): # BF don't need wrapper 
        if not snapshot:
            return
        
        # Power down the existing machine
        # Since the machine was started in a different session, 
        # it needs to be relocked to enable the shutdown functionality
        shutdown_vm(vmanager, vm, vsession)

        # Create a new session to re-lock the machine
        vsession = vmanager.getSessionObject()
        vsession.unlockMachine()

    vm.lockMachine(vsession, vmanager.constants.LockType_Shared)
    
    # Calling lockMachine creates a second machine object, which is where changes can be made
    # The self.mach IMachine object must be replaced by the new one, which is found in the session object
    vm = vsession.machine
    
    if snapshot:
        # Restores the desired snapshot and unlocks the machine to allow the new session to relock it
        progress = vm.restoreSnapshot(vm.findSnapshot(snapshot))
        progress.waitForCompletion(60000)
    
    vsession.unlockMachine()
    
    # Reset the machine and get a new session to launch the VM
    vm = vbox.findMachine(vname)
    vsession = vmanager.getSessionObject(vbox)
    
    # Sleep to allow the new session to initialize (it does not work without this)
    time.sleep(2)    
    progress = vm.launchVMProcess(vsession, 'gui', [])
    progress.waitForCompletion(90000)
    
    # Waits for the VM to fully start up
    time.sleep(30)
    
    if not vm_is_running(vmanager, vm):
        raise Exception('VM failed to sucessfully start')


def shutdown_vm(
    vmanager: vboxapi.VirtualBoxManager,
    vm,
    vsession,
):
    '''Closes the given VirtualBox VM. If the VM is already closed, do nothing.

    Args:
        vmanager (VirtualBoxManager):   VirtualBox Manager object.
        vm:                             VirtualBox virtual machine.
        vsession:                       VirtualBox VM session.
    Returns:
        None
    '''
    if not vm_is_running(vmanager, vm):
        return

    try:
        vm.lockMachine(vsession, vmanager.constants.LockType_Shared) # BF check error code
        progress = vsession.console.powerDown()
        progress.waitForCompletion(90000)
        vsession.unlockMachine()
    except:
        vsession.unlockMachine()
        raise


def mount_iso(
    iso_path: str,
    vmanager: vboxapi.VirtualBoxManager,
    vbox,
    vm,
    vsession
):
    '''Mounts the ISO at the given path to the given VirtualBox VM.
    
    Args:
        iso_path (str):                 path to the ISO image to mount.
        vmanager (VirtualBoxManager):   VirtualBox Manager object.
        vbox:                           VirtualBox singleton object.
        vm:                             VirtualBox virtual machine.
        vsession:                       VirtualBox VM session.
    Returns:
        None
    '''
    dvdMedium = None

    try:
        vm.lockMachine(vsession, vmanager.constants.LockType_Shared)
        dvdMedium = vbox.openMedium(iso_path, vmanager.constants.DeviceType_DVD,
                                    vmanager.constants.AccessMode_ReadOnly, False)
        vsession.machine.mountMedium("IDE Controller", 0, 0, dvdMedium, True)
        vsession.unlockMachine()
    except:
        vsession.unlockMachine()
        raise
    

def vm_is_running(
    vmanager: vboxapi.VirtualBoxManager,
    vm,
):
    '''Determine if a VirtualBox VM is running.

    Args:
        vmanager (VirtualBoxManager):   VirtualBox Manager object.
        vm:                             VirtualBox virtual machine.
    Returns:
        vm_is_running (bool):   True if the VM is on, else False
    '''
    return vm.state == vmanager.constants.MachineState_Running