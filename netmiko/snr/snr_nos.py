from netmiko.cisco_base_connection import CiscoSSHConnection
from netmiko import log
from netmiko.netmiko_globals import MAX_BUFFER

import re
import time


class SNRSSH(CiscoSSHConnection):
    def session_preparation(self):
        """
        Prepare the session after the connection has been established

        This method handles some differences that occur between various devices
        early on in the session.

        In general, it should include:
        self._test_channel_read()
        self.set_base_prompt()
        self.disable_paging()
        self.set_terminal_width()
        self.clear_buffer()
        """
        self._test_channel_read()
        self.set_base_prompt()
        self.enable()
        self.disable_paging()
        self.exit_enable_mode()
        self.set_terminal_width()

        # Clear the read buffer
        time.sleep(.3 * self.global_delay_factor)
        self.clear_buffer()


class SNRNosTelnet(SNRSSH):
    """SNR NOS Telnet driver."""
    pass


class SNRNosSerial(SNRSSH):
    """SNR NOS Serial driver."""
    def serial_login(self, pri_prompt_terminator=r'#\s*$', alt_prompt_terminator=r'>\s*$',
                     username_pattern=r"Username:\s*$", pwd_pattern=r"assword:\s*$",
                     delay_factor=3, max_loops=10):
        self.write_channel(self.TELNET_RETURN)
        time.sleep(2)
        output = self.read_channel()
        if (re.search(pri_prompt_terminator, output, flags=re.M)
            or re.search(alt_prompt_terminator, output, flags=re.M)):
            return output
        i = 1
        while i <= max_loops:
            self.write_channel(self.TELNET_RETURN)
            time.sleep(2)
            output = self.read_channel()
            if re.search('User Access Verification', output, flags=re.M):
                self.write_channel(self.username + '\n')
                time.sleep(1)
                self.write_channel(self.password + '\n')
                time.sleep(1)
            output = self.read_channel()
            if (re.search(pri_prompt_terminator, output, flags=re.M)
                or re.search(alt_prompt_terminator, output, flags=re.M)):
                return output
            i += 1
        return self.telnet_login(pri_prompt_terminator, alt_prompt_terminator,
                                     username_pattern, pwd_pattern, delay_factor, max_loops)

    def _read_channel(self):
        output = ""
        if self.protocol == 'ssh':
            while True:
                if self.remote_conn.recv_ready():
                    outbuf = self.remote_conn.recv(MAX_BUFFER)
                    if len(outbuf) == 0:
                        raise EOFError("Channel stream closed by remote device.")
                    output += outbuf.decode('utf-8', 'ignore')
                else:
                    break
        elif self.protocol == 'telnet':
            output = self.remote_conn.read_very_eager().decode('utf-8', 'ignore')
        elif self.protocol == 'serial':
            output = ""
            while (self.remote_conn.in_waiting > 0):
                output += self.remote_conn.read(self.remote_conn.in_waiting).decode('utf-8', 'ignore')
        log.debug("read_channel: {}".format(output))
        return output
