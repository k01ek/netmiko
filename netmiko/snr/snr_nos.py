from netmiko.cisco_base_connection import CiscoSSHConnection
from netmiko.ssh_exception import NetMikoAuthenticationException
import re
import time


class SNRSSH(CiscoSSHConnection):
    def serial_login(self, pri_prompt_terminator=r'#\s*$', alt_prompt_terminator=r'>\s*$',
                     username_pattern=r"(?:[Uu]ser:|sername|ogin)", pwd_pattern=r"assword",
                     delay_factor=1, max_loops=20):
        self.write_channel(self.TELNET_RETURN)
        output = self.read_channel()
        if (re.search(pri_prompt_terminator, output, flags=re.M)
            or re.search(alt_prompt_terminator, output, flags=re.M)):
            return output
        else:
            return self.telnet_login(pri_prompt_terminator, alt_prompt_terminator,
                                     username_pattern, pwd_pattern, delay_factor, max_loops)

    def telnet_login(self, pri_prompt_terminator=r'#\s*$', alt_prompt_terminator=r'>\s*$',
                     username_pattern=r"(?:user:|username|login|user name)",
                     pwd_pattern=r"assword",
                     delay_factor=1, max_loops=20):
        """Telnet login. Can be username/password or just password."""
        delay_factor = self.select_delay_factor(delay_factor)
        time.sleep(1 * delay_factor)

        output = ''
        return_msg = ''
        i = 1
        while i <= max_loops:
            try:
                output = self.read_channel()
                return_msg += output

                # Search for username pattern / send username
                if re.search(username_pattern, output, flags=re.I):
                    self.write_channel(self.username + self.TELNET_RETURN)
                    time.sleep(1 * delay_factor)
                    output = self.read_channel()
                    return_msg += output

                # Search for password pattern / send password
                if re.search(pwd_pattern, output, flags=re.I):
                    self.write_channel(self.password + self.TELNET_RETURN)
                    time.sleep(.5 * delay_factor)
                    output = self.read_channel()
                    return_msg += output
                    if (re.search(pri_prompt_terminator, output, flags=re.M)
                        or re.search(alt_prompt_terminator, output, flags=re.M)):
                        return return_msg

                # Support direct telnet through terminal server
                if re.search(r"initial configuration dialog\? \[yes/no\]: ", output):
                    self.write_channel("no" + self.TELNET_RETURN)
                    time.sleep(.5 * delay_factor)
                    count = 0
                    while count < 15:
                        output = self.read_channel()
                        return_msg += output
                        if re.search(r"ress RETURN to get started", output):
                            output = ""
                            break
                        time.sleep(2 * delay_factor)
                        count += 1

                # Check for device with no password configured
                if re.search(r"assword required, but none set", output):
                    self.remote_conn.close()
                    msg = "Login failed - Password required, but none set: {}".format(
                        self.host)
                    raise NetMikoAuthenticationException(msg)

                # Check if proper data received
                if (re.search(pri_prompt_terminator, output, flags=re.M)
                    or re.search(alt_prompt_terminator, output, flags=re.M)):
                    return return_msg

                self.write_channel(self.TELNET_RETURN)
                time.sleep(.5 * delay_factor)
                i += 1
            except EOFError:
                self.remote_conn.close()
                msg = "Login failed: {}".format(self.host)
                raise NetMikoAuthenticationException(msg)

        # Last try to see if we already logged in
        self.write_channel(self.TELNET_RETURN)
        time.sleep(.5 * delay_factor)
        output = self.read_channel()
        return_msg += output
        if (re.search(pri_prompt_terminator, output, flags=re.M)
            or re.search(alt_prompt_terminator, output, flags=re.M)):
            return return_msg

        self.remote_conn.close()
        msg = "Login failed: {}".format(self.host)
        raise NetMikoAuthenticationException(msg)


class SNRNosTelnet(SNRSSH):
    """SNR NOS Telnet driver."""
    pass


class SNRNosSerial(SNRSSH):
    """SNR NOS Serial driver."""
    pass
