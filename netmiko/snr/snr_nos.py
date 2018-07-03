from netmiko.cisco_base_connection import CiscoSSHConnection

import re
import time


class SNRSSH(CiscoSSHConnection):
    pass


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
