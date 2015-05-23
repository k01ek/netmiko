'''
Create a SCP side-channel to transfer a file to remote network device.

SCP requires a separate SSH connection.

Currently only supports Cisco IOS.
'''

from __future__ import print_function
from __future__ import unicode_literals

import re
import os
import hashlib

import paramiko
import scp

from netmiko.ssh_dispatcher import ConnectHandler


class SCPConn(object):
    '''
    Establish an SCP channel to the remote network
    '''

    def __init__(self, ssh_conn):
        self.ssh_ctl_chan = ssh_conn
        self.establish_scp_conn()


    def establish_scp_conn(self):
        '''
        Establish the SCP connection
        '''
        self.scp_conn = paramiko.SSHClient()
        self.scp_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.scp_conn.connect(hostname=self.ssh_ctl_chan.ip,
                              port=self.ssh_ctl_chan.port,
                              username=self.ssh_ctl_chan.username,
                              password=self.ssh_ctl_chan.password,
                              look_for_keys=False,
                              allow_agent=False,
                              timeout=8)

        self.scp_client = scp.SCPClient(self.scp_conn.get_transport())


    def scp_transfer_file(self, source_file, dest_file):
        '''
        Transfer file using SCP
        '''

        print("Transferring file: {}".format(source_file))
        self.scp_client.put(source_file, dest_file)


    def close(self):
        '''
        Close the SCP connection
        '''

        self.scp_conn.close()



class FileTransfer(object):
    '''
    Class to manage SCP file transfer and associated SSH control channel
    '''

    def __init__(self, ssh_conn, source_file, dest_file, file_system="flash:"):
        '''
        Establish a SCP connection to the remote network device
        '''
        self.scp_conn = SCPConn(self.ssh_ctl_chan)

        self.source_file = source_file
        self.source_md5 = self.file_md5(source_file)
        self.dest_file = dest_file
        self.file_system = file_system

        src_file_stats = os.stat(source_file)
        self.file_size = src_file_stats.st_size


    def close_scp_chan(self):
        '''
        Close the SCP connection to the remote network device
        '''
        self.scp_conn.close()
        self.scp_conn = None


    def verify_space_available(self, search_pattern=r"(.*) bytes available "):
        '''
        Verify sufficient space is available on remote network device

        Return a boolean
        '''
        remote_cmd = "show {0}".format(self.file_system)
        remote_output = self.ssh_ctl_chan.send_command(remote_cmd)
        match = re.search(search_pattern, remote_output)
        space_avail = int(match.group(1))

        if space_avail > self.file_size:
            return True
    
        return False


    def check_file_exists(self, remote_cmd=""):
        '''
        Check if the dest_file exists on the remote file system

        Return a boolean
        '''

        if not remote_cmd:
            remote_cmd = "dir flash:/{0}".format(self.dest_file)

        remote_out = self.ssh_ctl_chan.send_command(remote_cmd)

        search_string = r"Directory of .*{0}".format(self.dest_file)
        if 'Error opening' in remote_out:
            return False
        elif re.search(search_string, remote_out):
            return True
        else:
            raise ValueError("Unexpected output from check_file_exists")


    @staticmethod
    def file_md5(file_name):
        '''
        Compute MD5 hash of file
        '''
        with open(file_name, "rb") as f:
            file_contents = f.read()
            file_hash = hashlib.md5(file_contents).hexdigest()
        return file_hash


    @staticmethod
    def process_md5(md5_output, pattern=r"= (.*)"):
        '''
        Process the string to retrieve the MD5 hash
   
        Output from Cisco IOS: 
        .MD5 of flash:file_name Done!
        verify /md5 (flash:file_name) = 410db2a7015eaa42b1fe71f1bf3d59a2
        '''
        match = re.search(pattern, md5_output)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid output from MD5 command: {0}".format(md5_output))


    def compare_md5(self, base_cmd='verify /md5'):
        '''
        Calculate remote MD5 and compare to source MD5

        Default command is Cisco specific

        Return boolean
        '''
        remote_md5_cmd = "{0} {1}".format(base_cmd, self.dest_file)

        dest_md5 = self.ssh_ctl_chan.send_command(remote_md5_cmd)
        dest_md5 = self.process_md5(dest_md5)
        if self.source_md5 != dest_md5:
            return False
        else:
            return True


    def transfer_file(self):
        '''
        SCP transfer source_file to Cisco IOS device

        Verifies MD5 of file on remote device or generates an exception
        '''

        self.open_scp_chan()
        self.scp_conn.scp_transfer_file(self.source_file, self.dest_file)
        self.close_scp_chan()


    def verify_file(self):
        '''
        Verify the file has been transferred correctly
        '''
        return self.compare_md5()




