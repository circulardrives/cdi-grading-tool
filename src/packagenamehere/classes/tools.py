"""
Circular Drive Initiative - Toolkit Classes

@language Python 3.12
@version  0.0.1
"""

# Modules
import json
import subprocess

# Date and Time
from datetime import datetime

# Exceptions
from packagenamehere.classes.exceptions import CommandException


class Command:
    """
    Command Class
    """

    def __init__(self, command: str = None):
        """
        Constructor
        :param command:
        """

        # Properties
        self.command = ' '.join(command.split()) if command else None
        self.arguments = None
        self.process = None
        self.process_id = None
        self.return_code = None
        self.output = None
        self.errors = None
        self.started = None
        self.finished = None
        self.duration = None

    def run(self):
        """
        Run
        :return:
        """

        # Try
        try:
            # Start Time
            start_time = datetime.now()

            # Launch Process
            self.process = subprocess.Popen(
                self.command.split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Capture Args
            self.arguments = self.process.args

            # Capture Output
            self.output, self.errors = self.process.communicate()

            # Capture Return Code
            self.return_code = self.process.returncode

            # Capture Process ID
            self.process_id = self.process.pid

            # Finished Time
            finished_time = datetime.now()

            # Start Time
            self.started = start_time.strftime("%d/%m/%Y %H:%M:%S")

            # End Time
            self.finished = finished_time.strftime("%d/%m/%Y %H:%M:%S")

            # Capture Process Duration
            self.duration = str(finished_time - start_time)

        # If FileNotFoundError
        except FileNotFoundError:

            # Raise Command Exception
            raise CommandException("Command not found")

        # If Exception
        except Exception:

            # Raise Command Exception
            raise CommandException("An Error occurred while running the Command")

    def get_command(self):
        """
        Command Property
        :return:
        """

        return self.command

    def get_arguments(self):
        """
        Arguments Property
        :return:
        """

        return self.arguments

    def get_return_code(self):
        """
        Return Code Property
        :return:
        """

        return self.return_code

    def get_process_id(self):
        """
        Process ID Property
        :return:
        """

        return self.process_id

    def get_output(self):
        """
        Output Property
        :return:
        """

        return self.output

    def get_errors(self):
        """
        Errors Property
        :return:
        """

        return self.errors

    def get_duration(self):
        """
        Duration Property
        :return:
        """

        return self.duration

    def get_dictionary(self):
        """
        Get Dictionary
        :return:
        """

        # Return Dictionary
        return dict(
            arguments=self.get_arguments(),
            return_code=self.get_return_code(),
            process_id=self.get_process_id(),
            output=self.get_output(),
            errors=self.get_errors(),
            duration=self.get_duration()
        )

    def has_errors(self):
        """
        Has Errors Property
        :return:
        """

        # If Return Code is not 0
        if self.return_code != 0:
            return True

        return False

    def terminate(self):
        """
        Terminate Command
        :return:
        """

        # If Process
        if self.process:
            # Terminate Process
            self.process.terminate()

        # Return True
        return True


class SeaTools:
    """
    SeaTools Class
    """

    # Get Commands
    get_version_command = '/opt/openSeaChest/openSeaChest_Basics --version'
    get_devices_command = '/opt/openSeaChest/openSeaChest_Basics --scan'
    get_device_information_command = '/opt/openSeaChest/openSeaChest_Basics --deviceInfo --device'

    # Self Test Commands
    abort_self_test_command = '/opt/openSeaChest/openSeaChest_SMART --abortDST --device'
    execute_self_test_short_command = '/opt/openSeaChest/openSeaChest_SMART --shortDST --device'
    execute_self_test_long_command = '/opt/openSeaChest/openSeaChest_SMART --longDST --device'
    execute_self_test_conveyance_command = '/opt/openSeaChest/openSeaChest_SMART --conveyanceDST --device'

    def __init__(self, device_id: str = None):
        """
        Smartctl
        :param device_id:
        """

        # Device ID
        self.dut = device_id

    """
    Device Information Commands
    """

    def get_all_as_text(self):
        """
        Get All as Text
        :return:
        """

        # Prepare Command String
        get_all_command = f'{self.get_device_information_command} {self.dut}'

        # Prepare Command
        command = Command(get_all_command)

        # Run Command
        command.run()

        # If Return Code is not Zero
        if command.get_return_code() != 0:
            # Return False
            return False

        # Return Smartctl Output as Text
        return command.get_output().strip().decode('utf-8')

    """
    Self-test Commands
    """

    def abort_self_test(self):
        """
        Execute Abort Self-test
        :return: Command
        """

        # Prepare Command String
        short_self_test = f'{self.abort_self_test_command} {self.dut}'

        # Prepare Command
        command = Command(short_self_test)

        # Run Command
        command.run()

        # Return
        return command

    def execute_self_test_short(self, captive: bool = False, force: bool = False) -> Command:
        """
        Execute Short Self-test
        :param force: force the execution of a new test, aborting the current test (if any)
        :param captive: run the short test in captive mode (defaults to background mode)
        :return: Command
        """

        # Prepare Command String
        short_self_test = f'{self.execute_self_test_short_command} {"force" if force else " "}{"-C" if captive else " "}{self.dut}'

        # Prepare Command
        command = Command(short_self_test)

        # Run Command
        command.run()

        # Return
        return command

    def execute_self_test_long(self, captive: bool = False, force: bool = False) -> Command:
        """
        Execute Extended Self-test
        WARNING - This test will take a long time to complete as it processes the entire device
        :param force: force the execution of a new test, aborting the current test (if any)
        :param captive: run the extended test in captive mode (defaults to background mode)
        :return: Command
        """

        # Prepare Command String
        extended_self_test_command = f'{self.execute_self_test_long_command} {"force" if force else ""} {"-C" if captive else ""} {self.dut}'

        # Prepare Command
        command = Command(extended_self_test_command)

        # Run Command
        command.run()

        # Return
        return command

    def execute_self_test_conveyance(self, captive: bool = False, force: bool = False) -> Command:
        """
        Execute Conveyance Self-test
        :param force: force the execution of a new test, aborting the current test (if any)
        :param captive: run the conveyance test in captive mode (defaults to background mode)
        :return: Command
        """

        # Prepare Command String
        conveyance_self_test_command = f'{self.execute_self_test_conveyance_command} {"force" if force else ""} {"-C" if captive else ""} {self.dut}'

        # Prepare Command
        command = Command(conveyance_self_test_command)

        # Run Command
        command.run()

        # Return
        return command


class SG3Utils:
    """
    SG3Utils Class
    """

    def __init__(self, device_id: str):
        """
        Constructor
        """

        # Properties
        self.dut = device_id

    def sg_map26(self) -> str | bool:
        """
        Map26 Command
        Returns the SCSI Generic ID for the Block Device
        :return str SCSI Generic ID | bool False for Failure:
        """

        # If is NVMe
        if '/dev/nvme' in self.dut:
            # Return DUT
            return self.dut

        # Try
        try:
            # Set Command
            command = Command(f'sg_map26 {self.dut}')

            # Run Command
            command.run()

            # If Return Code is not Zero
            if command.get_return_code() != 0:
                # Return False
                return False

            # Return SCSI Generic DUT
            return command.get_output().strip().decode('utf-8')

        # If Command Exception
        except CommandException:
            # Return False
            return False

    def test_unit_ready(self):
        # If is NVMe
        if '/dev/nvme' in self.dut:
            # Return DUT
            return self.dut

        # Try
        try:
            # Set Command
            command = Command(f'sg_turs -vvvv {self.dut}')

            # Run Command
            command.run()

            # If Return Code is not Zero
            if command.get_return_code() != 0:
                # Return False
                return "Not Ready"

            # Return Ready
            return "Ready"

        # If Command Exception
        except CommandException:
            # Return False
            return False


class Smartctl:
    """
    Smartctl Class
    """

    # Get Commands
    get_version_command = 'smartctl --version'
    get_devices_command = 'smartctl --scan'
    get_devices_open_command = 'smartctl --scan-open'
    get_identify_command = 'smartctl --identify'
    get_identity_command = 'smartctl --info'
    get_health_command = 'smartctl --health'
    get_device_information_command = 'smartctl --all'
    get_all_device_information_command = 'smartctl --xall'

    # S.M.A.R.T Commands
    set_enable_smart_command = 'smartctl --smart=on'
    set_disable_smart_command = 'smartctl --smart=off'
    set_enable_smart_automatic_offline_testing_command = 'smartctl --offlineauto=on'
    set_disable_smart_automatic_offline_testing_command = 'smartctl --offlineauto=off'
    set_enable_smart_automatic_attribute_autosave_command = 'smartctl --saveauto=on'
    set_disable_smart_automatic_attribute_autosave_command = 'smartctl --saveauto=off'
    set_enable_smart_all_options = 'smartctl --smart=off --offlineauto=off --saveauto=off'
    set_disable_smart_all_options = 'smartctl --smart=off --offlineauto=off --saveauto=off'

    # Self Test Commands
    abort_self_test_command = 'smartctl --abort --json=ov'
    execute_self_test_offline_command = 'smartctl --test=offline --json=ov'
    execute_self_test_short_command = 'smartctl --test=short --json=ov'
    execute_self_test_long_command = 'smartctl --test=long --json=ov'
    execute_self_test_conveyance_command = 'smartctl --test=conveyance --json=ov'
    execute_self_test_selective_command = 'smartctl --test=select'
    execute_self_test_vendor_specific_command = 'smartctl --test=vendor'

    def __init__(self, device_id: str = None):
        """
        Smartctl
        :param device_id:
        """

        # Set Device ID
        self.dut = device_id

        # Set Acceptable Return Codes
        self.acceptable_return_codes = [
            0,
            4,
            64,
            192,
            196,
            216
        ]

        # Set Bit Mask Codes
        self.bitmask_codes = {
            0: "Command line did not parse correctly",
            1: "Device open failed, or device did not return an IDENTIFY DEVICE structure",
            2: "S.M.A.R.T command failed, or there was a checksum error in the S.M.A.R.T data structure",
            3: "S.M.A.R.T Status returned 'DISK FAILING'",
            4: "S.M.A.R.T Status returned 'DISK OK' but found pre-fail attributes that have previously exceeded threshold",
            5: "S.M.A.R.T Status returned 'DISK OK' but found usage or pre-fail attributes have previously exceeded threshold in the past",
            6: "S.M.A.R.T Error Log contains 1 or more record of errors",
            7: "S.M.A.R.T Self-test Log contains 1 or more record of failed self-tests",
        }

    """
    Helpers
    """

    def get_version(self) -> str | bool:
        """
        Get Version
        :return: Version if successful | False if not
        """

        # Prepare Command String
        get_version_command = f'{self.get_version_command} {self.dut}'

        # Prepare Command
        command = Command(get_version_command)

        # Run Command
        command.run()

        # If Return Code is not Zero
        if command.get_return_code() not in self.acceptable_return_codes:
            # Return False
            return False

        # Return Smartctl Output as Text
        return command.get_output().strip().decode('utf-8')

    """
    Device Information Commands
    """

    def get_all_as_text(self):
        """
        Get All as Text
        :return:
        """

        # Prepare Command String
        get_all_command = f'{self.get_all_device_information_command} {self.dut}'

        # Prepare Command
        command = Command(get_all_command)

        # Run Command
        command.run()

        # If Return Code is not Zero
        if command.get_return_code() not in self.acceptable_return_codes:
            # Return False
            return False

        # Return Smartctl Output as Text
        return command.get_output().strip().decode('utf-8')

    def get_all_as_json(self) -> dict | bool:
        """
        Get All as JSON
        :return: dict if OK | False if not
        """

        # Prepare Command String
        get_all_command = f'{self.get_all_device_information_command} {self.dut} --json=ov'

        # Prepare Command
        command = Command(get_all_command)

        # Run Command
        command.run()

        # If Return Code is not Zero
        if command.get_return_code() != 0:
            # Loop through Bitmask
            for bit_position, error_message in self.bitmask_codes.items():
                # Check if Bit is Set
                if command.get_return_code() & (1 << bit_position):
                    # Print Error
                    # print(f"{self.dut} - {error_message}")
                    pass

        # Return Smartctl Output as JSON
        return json.loads(command.get_output().strip().decode('utf-8'))

    def get_health(self, as_json=True):
        """
        Get Health
        :return: Command
        """

        # Prepare Command String
        get_health = f'{self.get_health_command} {"--json=ov" if as_json else ""} {self.dut}'

        # Prepare Command
        command = Command(get_health)

        # Run Command
        command.run()

        # Return
        return command

    """
    Self-test Commands
    """

    def abort_self_test(self):
        """
        Execute Abort Self-test
        :return: Command
        """

        # Prepare Command String
        short_self_test = f'{self.abort_self_test_command} {self.dut}'

        # Prepare Command
        command = Command(short_self_test)

        # Run Command
        command.run()

        # Return
        return command

    def execute_self_test_offline(self, captive: bool = False, force: bool = False) -> Command:
        """
        Execute Offline Self-test
        :param force: force the execution of a new test, aborting the current test (if any)
        :param captive: run the offline test in captive mode (defaults to background mode)
        :return: Command
        """

        # Prepare Command String
        short_self_test = f'{self.execute_self_test_offline_command} {"force" if force else " "}{"-C" if captive else " "}{self.dut}'

        # Prepare Command
        command = Command(short_self_test)

        # Run Command
        command.run()

        # Return
        return command

    def execute_self_test_short(self, captive: bool = False, force: bool = False) -> Command:
        """
        Execute Short Self-test
        :param force: force the execution of a new test, aborting the current test (if any)
        :param captive: run the short test in captive mode (defaults to background mode)
        :return: Command
        """

        # Prepare Command String
        short_self_test = f'{self.execute_self_test_short_command} {"force" if force else " "}{"-C" if captive else " "}{self.dut}'

        # Prepare Command
        command = Command(short_self_test)

        # Run Command
        command.run()

        # Return
        return command

    def execute_self_test_long(self, captive: bool = False, force: bool = False) -> Command:
        """
        Execute Extended Self-test
        WARNING - This test will take a long time to complete as it processes the entire device
        :param force: force the execution of a new test, aborting the current test (if any)
        :param captive: run the extended test in captive mode (defaults to background mode)
        :return: Command
        """

        # Prepare Command String
        extended_self_test_command = f'{self.execute_self_test_long_command} {"force" if force else ""} {"-C" if captive else ""} {self.dut}'

        # Prepare Command
        command = Command(extended_self_test_command)

        # Run Command
        command.run()

        # Return
        return command

    def execute_self_test_conveyance(self, captive: bool = False, force: bool = False) -> Command:
        """
        Execute Conveyance Self-test
        :param force: force the execution of a new test, aborting the current test (if any)
        :param captive: run the conveyance test in captive mode (defaults to background mode)
        :return: Command
        """

        # Prepare Command String
        conveyance_self_test_command = f'{self.execute_self_test_conveyance_command} {"force" if force else ""} {"-C" if captive else ""} {self.dut}'

        # Prepare Command
        command = Command(conveyance_self_test_command)

        # Run Command
        command.run()

        # Return
        return command

    def execute_self_test_selective(self, starting_lba=0, ending_lba=100, captive: bool = False, force: bool = False, after_select: bool = False):
        """
        Execute Selective Self-test
        :param starting_lba: the lba to start test from
        :param ending_lba: the lba to end test on
        :param captive: run the conveyance test in captive mode (defaults to background mode)
        :param force: force the execution of a new test, aborting the current test (if any)
        :param after_select: perform an after-select test (defaults to False)
        :return: Command
        """

        # Prepare Command String
        selective_self_test_command = f'{self.execute_self_test_selective_command},{starting_lba}-{ending_lba} {"afterselect,on" if after_select else " "}{"force" if force else " "}{"-C" if captive else " "}{self.dut}'

        # Prepare Command
        command = Command(selective_self_test_command)

        # Run Command
        command.run()

        # Return
        return command

    def execute_self_test_vendor_specific(self, vendor_specific_command: str = "0x00", captive: bool = False, force: bool = False) -> Command:
        """
        Execute Vendor Self-test
        :param vendor_specific_command: the Vendor specific command to pass with the Self-test
        :param force: force the execution of a new test, aborting the current test (if any)
        :param captive: run the vendor specific test in captive mode (defaults to background mode)
        :return: Command
        """

        # Prepare Command String
        short_self_test = f'{self.execute_self_test_vendor_specific_command},{vendor_specific_command} {"force" if force else " "}{"-C" if captive else " "}{self.dut}'

        # Prepare Command
        command = Command(short_self_test)

        # Run Command
        command.run()

        # Return
        return command
