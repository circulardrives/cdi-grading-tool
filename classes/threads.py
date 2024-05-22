"""
Circular Drive Initiative - Thread Classes

@language    Python 3.12
@framework   PySide 6
@version     0.0.1
"""

# Modules
import json
import time
import uuid

# Date and Time
from datetime import datetime, timedelta

# PySide6
from PySide6.QtCore import QThread, Signal, QSemaphore

# Classes
from classes.devices import Device, Devices
from classes.helpers import Report
from classes.tools import Command

# Exceptions
from classes.exceptions import Cancelled, DeviceLost, SMARTFail, SMARTSelfTestFail, SMARTHistoricSelfTestFail, ReallocatedSectorsExceedsThreshold, PendingSectorsExceedsThreshold, CommandException

# Constants
from constants import pending_progress_bar, grade_a, pass_badge, pass_progress_bar, failed_progress_bar, failed_badge, CDI_MAXIMUM_REALLOCATED_SECTORS, CDI_MAXIMUM_PENDING_SECTORS


class Grading(QThread):
    """
    Grading Thread
    """

    # Standard Signals
    finished = Signal()
    cancelled = Signal()
    terminated = Signal()

    # User Interface Signals
    update_control_list = Signal(dict)
    update_capacity = Signal(str)
    update_state = Signal(str)
    update_message = Signal(str)
    update_comments = Signal(str)
    update_console = Signal(str)
    update_result = Signal(str)
    update_result_style = Signal(str)
    update_grade = Signal(str)
    update_grade_style = Signal(str)
    update_progress = Signal(int)
    update_progress_style = Signal(str)
    update_device_state = Signal(str, str)

    # Licenses Remaining Signal
    update_licenses_remaining = Signal(str)

    # Error Signal
    raise_error_dialog = Signal(str, dict, dict)

    def __init__(self, device) -> None:
        """
        Constructor
        :param device: Device to process
        :return: None
        """

        # Initialize
        super(Grading, self).__init__()

        # Get Device
        self.device = device

        # Reset Grade
        self.grade = "U"

        # Session Properties
        self.id: str = str(uuid.uuid4())

        # Session Flags
        self.is_certified_for_reuse: bool = False
        self.was_cancelled: bool = False

        # Test Report
        self.report: Report = Report()

        # Semaphore
        self.semaphore = QSemaphore(1)

    def run(self) -> bool:
        """
        Run Grading Thread
        :return: bool
        """

        # Try
        try:
            # Get Device
            self.get_device()

            # Create Report
            self.create_report()

            # Do Grading
            self.execute_grading()

            # Do Report Generation
            self.create_test_report()

            # Do Standby Device
            self.execute_standby_device()

            # Emit Finished
            self.finished.emit()

            # Return
            return True

        # If Cancelled
        except Cancelled as cancelled_exception:
            # Set Cancelled
            self.set_report_cancelled(cancelled_exception)

            # Print to Console
            self.print_exception(device=self.device, exception=cancelled_exception)

            # Create Report
            self.create_test_report()

            # Emit Finished
            self.finished.emit()

            # Return False
            return False

        # If SMART Failure
        except DeviceLost | SMARTFail | SMARTSelfTestFail | SMARTHistoricSelfTestFail | ReallocatedSectorsExceedsThreshold | PendingSectorsExceedsThreshold as exception:
            # Set Cancelled
            self.set_report_fail(exception)

            # Print to Console
            self.print_exception(device=self.device, exception=exception)

            # Create Report
            self.create_test_report()

            # Emit Finished
            self.finished.emit()

            # Return False
            return False

    def run_ata_grading(self):
        """
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # ATA Grading Schedule - CDI Grading Tool - 2024
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # # - Description ----------------------- Value ------------------------------------------------------
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 1 - S.M.A.R.T Health                    Must Pass                                               Done
        # 2 - S.M.A.R.T Short Self-test           Must Pass                                               Done
        # 3 - S.M.A.R.T Conveyance Self-test      Must Pass                                           Optional
        # 4 - S.M.A.R.T Vendor-specific Self-test Must Pass                                           Optional
        # 4 - S.M.A.R.T Historical Self-test Logs Must not contain 'failed' historical self-test results  Done
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 5 - S.M.A.R.T Attributes Analysis
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 5a - No Attribute Thresholds exceeded (by vendor specific threshold) == dynamic
        # 5b - Attribute 5 - Reallocated Sectors (HDD) / Reallocated NAND Blocks (SSD) < 10
        # 5c - Attribute 196 - Pending Reallocated Sectors (HDD) / Pending Reallocated NANO Blocks (SSD) < 10
        # 5d - Attribute 198 - Offline Uncorrectable Sectors (HDD/SSD) < 10
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 6 - Power On Hours - HDDs (10 years) / SSDs (5 years)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        """

        # Emit Messages
        self.update_state.emit("Grading")
        self.update_message.emit("Preparing ATA Grading Schedule...")

        # Emit Percent
        self.update_progress.emit(0)
        self.update_progress_style.emit(pending_progress_bar)

        # Check S.M.A.R.T Status
        self.check_smart_status()

        # Check S.M.A.R.T Historic Self-test Logs
        self.check_smart_historic_self_test_logs()

        # Execute S.M.A.R.T Short Self-test
        self.check_smart_short_self_test_status()

        # Execute S.M.A.R.T Short Self-test
        self.check_smart_vendor_self_test_status()

        # Execute Reallocated Sectors Check
        self.check_reallocated_sectors()

        # Execute Pending Sectors Check
        self.check_pending_sectors()

        # Execute Start/Stop Count Check
        self.check_start_stop_count()

        """ 
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        FINALIZE GRADING
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        """

        # Set Grade
        self.grade = grade_a
        self.update_grade.emit(grade_a)
        self.update_grade_style.emit(pass_badge)

        # Set Result
        self.update_result.emit("Pass")
        self.update_result_style.emit(pass_badge)

        # Set Certified False
        self.is_certified_for_reuse = True
        self.update_message.emit(f"Grading Complete")
        self.update_progress_style.emit(pass_progress_bar)
        self.update_comments.emit(f"Grading passed. Certified for Reuse.")

        # Update Report
        self.report['status'].update({
            'result': "Pass",
            'remarks': f"Grading completed successfully."
        })

        """ 
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        END FINALIZE GRADING
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        """

        # Return True
        return True

    def run_scsi_grading(self):
        """
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # SCSI Grading Schedule - CDI Grading Tool - 2024
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # # - Description ----------------------- Value ------------------------------------------------------
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 1 - S.M.A.R.T Health                    Must Pass                                               Done
        # 2 - S.M.A.R.T Short Self-test           Must Pass                                               Done
        # 3 - S.M.A.R.T Conveyance Self-test      Must Pass                                           Optional
        # 4 - S.M.A.R.T Vendor-specific Self-test Must Pass                                           Optional
        # 4 - S.M.A.R.T Historical Self-test Logs Must not contain 'failed' historical self-test results  Done
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 5 - S.M.A.R.T Attributes Analysis
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 5a - No Attribute Thresholds exceeded (by vendor specific threshold) == dynamic
        # 5b - Grown Defects/Reallocated Sectors (HDD) < 10
        # 5c - Total Uncorrectable Errors (HDD/SSD) < 10
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 6 - Power On Hours - HDDs (10 years) / SSDs (5 years)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        """

        # Emit Messages
        self.update_state.emit("Grading")
        self.update_message.emit("Preparing SCSI Grading Schedule...")

        # Emit Percent
        self.update_progress.emit(0)
        self.update_progress_style.emit(pending_progress_bar)

        # Check S.M.A.R.T Status
        self.check_smart_status()

        # Check S.M.A.R.T Historic Self-test Logs
        self.check_smart_historic_self_test_logs()

        # Execute S.M.A.R.T Short Self-test
        self.check_smart_short_self_test_status()

        # Execute S.M.A.R.T Short Self-test
        self.check_smart_vendor_self_test_status()

        # Execute Reallocated Sectors Check
        self.check_reallocated_sectors()

        """ 
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        FINALIZE GRADING
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        """

        # Set Grade
        self.grade = grade_a
        self.update_grade.emit(grade_a)
        self.update_grade_style.emit(pass_badge)

        # Set Result
        self.update_result.emit("Pass")
        self.update_result_style.emit(pass_badge)

        # Set Certified False
        self.is_certified_for_reuse = True
        self.update_message.emit(f"Grading Complete")
        self.update_progress_style.emit(pass_progress_bar)
        self.update_comments.emit(f"Grading passed. Certified for Reuse.")

        # Update Report
        self.report['status'].update({
            'result': "Pass",
            'remarks': f"Grading completed successfully."
        })

        """ 
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        END FINALIZE GRADING
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        """

        # Return True
        return True

    def stop(self):
        """
        Stop
        """

        # Acquire Semaphore
        self.semaphore.acquire()

    @staticmethod
    def print_exception(device, exception):
        """
        Print Exception
        :param device: the device
        :param exception: the exception
        """

        # Print to Console
        print(device.model_number, " --> ", exception)

    """
    Mandatory Diagnostics
    """

    def get_device(self):
        """
        Get Device Information
        """

        # Set State
        state = "Device"
        state_message = "Getting Device Information..."

        # Emit State
        self.update_progress.emit(1)
        self.update_state.emit(state)
        self.update_message.emit(state_message)

        # Try
        try:
            # Get Device
            self.device = Device(self.device['dut'])

            # Set Report Information
            self.report['device'] = self.device.__dict__

            # Emit
            self.update_state.emit(state)
            self.update_message.emit(state_message + ' OK')

        # If Exception
        except CommandException:
            # Return False
            pass

    def identify(self, args, post=False):
        """
        Identify Device
        """

        # Result
        self.report[f'{"pre" if not post else "post"}_test'][args['key']] = {
            'name': args['name'],
            'description': args['description'],
            'started': datetime.now(),
            'ended': datetime.now(),
            'result': 'Pass',
        }

    def request_sense(self, args, post=False):
        """
        Request Sense
        :param args:
        :param post:
        :return:
        """

        # Report
        self.report[f'{"pre" if not post else "post"}_test'][args['key']] = {
            'name': args['name'],
            'description': args['description'],
            'started': datetime.now(),
            'ended': datetime.now(),
            'result': 'Pass',
        }

    def test_unit_ready(self, args, post=False):
        """
        Test Unit Ready
        :param args:
        :param post:
        :return:
        """

        # Report
        self.report[f'{"pre" if not post else "post"}_test'][args['key']] = {
            'name': args['name'],
            'description': args['description'],
            'started': datetime.now(),
            'ended': datetime.now(),
            'result': 'Pass',
        }

    def read_capacity(self, args, post=False):
        """
        Read Capacity
        :param args:
        :param post:
        :return:
        """

        # Report
        self.report[f'{"pre" if not post else "post"}_test'][args['key']] = {
            'name': args['name'],
            'description': args['description'],
            'started': datetime.now(),
            'ended': datetime.now(),
            'result': 'Pass',
        }

    def check_condition(self, args, post=False):
        """
        Check Condition
        :param args:
        :param post:
        :return:
        """

        # Report
        self.report[f'{"pre" if not post else "post"}_test'][args['key']] = {
            'name': args['name'],
            'description': args['description'],
            'started': datetime.now(),
            'ended': datetime.now(),
            'result': 'Pass',
        }

    """
    Grading
    """

    def execute_grading(self):
        """
        Execute Grading
        :return:
        """

        # Refresh Device
        self.device.refresh()

        # ATA
        if self.device.is_ata:
            # Run ATA Grading
            self.run_ata_grading()

        # NVMe
        if self.device.is_nvme:
            # Run NVMe Grading
            self.run_nvme_grading()

        # ATA
        if self.device.is_scsi:
            # Run ATA Grading
            self.run_scsi_grading()

    def go_idle(self, section="Pre-Test", seconds=1, without_message=False):
        """
        Go Idle
        @param section:
        @param without_message:
        @param seconds:
        """

        # Idle
        idle_for = seconds

        # Timer
        timer = 0

        # While Timer
        while timer < idle_for:
            # Get Remaining Time
            remaining = idle_for - timer

            # If with Message
            if not without_message:
                # Emit Message
                self.update_message.emit(f"{section} complete - Idle for {remaining} seconds...")

            # Sleep
            time.sleep(1)

            # Decrement
            timer += 1

    """
    Standby
    """

    def execute_standby_device(self):
        """
        Execute Standby Device
        :return:
        """

        if self.device.is_ata:
            # Prepare Command
            command = Command(f'hdparm -y {self.device.dut}')

            # Run Command
            command.run()

        if self.device.is_nvme:
            pass

        if self.device.is_scsi:
            # Prepare Command
            command = Command(f'sg_start --stop {self.device.dut}')

            # Run Command
            command.run()

    """
    Reports
    """

    def create_report(self) -> dict:
        """
        Create Report
        :return: dict
        """

        # Report
        self.report: dict = {
            # ID Fields
            'id': {
                'device': self.id,
            },
            # Software Fields
            'software': {
                'software': 'CDI Grading Tool',
                'version': 1.0,
                'operating_system': 'Linux',
                'operating_system_distribution': 'Debian',
                'operating_system_version': 12,
                'toolkits': [
                    'hdparm',
                    'hdsentinel',
                    'nvme-cli',
                    'openseachest',
                    'smartctl',
                    'sg3-Utils',
                    'sedutil-cli'
                ]
            },
            # Device
            'device': {},
            # Test
            'test': {},
            # Validation
            'validate': {},
            # Grading
            'grade': {},
            # Overall Status
            'status': {},
        }

        # Return
        return self.report

    def set_report_cancelled(self, exception):
        pass

    def set_report_fail(self, exception):
        pass

    def create_test_report(self):
        """
        Create Test Report
        """

        # Set Reports Directory
        reports_dir = './reports/'

        # File Extension
        file_ext = '.json'

        # Set File Name
        filename = f"{self.device.model_number}-{self.device.serial_number}-{self.report['status']['result']}"

        # Create Test Report
        with open(reports_dir + filename + file_ext, 'w') as json_file:
            # Create JSON Test Report
            json.dump(self.report, json_file)

    def check_smart_status(self):
        """
        Check S.M.A.R.T Status
        """

        # Emit
        self.update_state.emit("S.M.A.R.T")

        # Start Time
        smart_status_start_time = datetime.now()

        # Report
        self.report['test']['smart_status'] = {
            'name': "S.M.A.R.T Status",
            'description': "S.M.A.R.T Status and Predictive Failure Analysis",
            'started': smart_status_start_time.strftime("%d/%m/%Y %H:%M:%S"),
            'finished': '',
            'duration': '',
            'threshold': 'Must Pass',
            'value': '',
            'result': '',
            'toolkit': f'smartctl',
            'command': f'smartctl --xall {self.device.dut}',
        }

        # Refresh Device
        self.device.refresh()

        # Finish Time
        smart_status_finish_time, smart_status_duration = datetime.now(), str(datetime.now() - smart_status_start_time)

        # Step 1 - Check S.M.A.R.T Health OK
        if not self.device.smart_status:
            # Set Grade to F
            self.grade = "F"

            # Set Certified for Reuse
            self.is_certified_for_reuse = False

            # Emit
            self.update_grade.emit("F")
            self.update_result.emit("FAIL")
            self.update_message.emit(f"Grading Complete - S.M.A.R.T is not OK - FAIL")
            self.update_comments.emit(f"S.M.A.R.T Status not OK. Not Certified for Reuse.")

            # Update Style
            self.update_progress.emit(100)
            self.update_progress_style.emit(failed_progress_bar)
            self.update_result_style.emit(failed_badge)
            self.update_grade_style.emit(failed_badge)

            # Update Report
            self.report['test']['smart_status'].update({
                'finished': smart_status_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
                'duration': smart_status_duration,
                'value': "Fail",
                'result': "Fail",
                'remarks': "S.M.A.R.T Status is not OK/Healthy. S.M.A.R.T must pass for CDI certification."
            })

            # Update Status
            self.report['status']['result'] = "Fail"
            self.report['status']['remarks'] = f"S.M.A.R.T status is not OK/Healthy."

            # S.M.A.R.T Fail
            raise SMARTFail("S.M.A.R.T status is not OK/Healthy.")

        # Update Report
        self.report['test']['smart_status'].update({
            'finished': smart_status_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
            'duration': smart_status_duration,
            'value': "Pass",
            'result': "Pass",
            'remarks': "S.M.A.R.T Status is OK."
        })

        # Emit
        self.update_comments.emit("S.M.A.R.T Status OK.")

    def check_smart_historic_self_test_logs(self):
        """
        Check S.M.A.R.T Historic Self-test Logs
        """

        # Start Time
        historic_self_test_logs_start_time = datetime.now()

        # If ATA Device
        if self.device.is_ata:
            # Skip if none-logged
            if self.device.smart_self_tests == "No Self Tests Logged":
                # Return
                return

            # Emit
            self.update_state.emit("Testing")

            # Report
            self.report['test']['smart_self_test_logs'] = {
                'name': "S.M.A.R.T Self-test Log Analysis",
                'description': "Historic S.M.A.R.T Self-test Log analysis.",
                'started': historic_self_test_logs_start_time.strftime("%d/%m/%Y %H:%M:%S"),
                'finished': '',
                'duration': '',
                'threshold': "Must contain no failed Self-tests",
                'value': '',
                'result': '',
                'logs': '',
                'toolkit': f'smartctl',
                'command': f'smartctl --xall {self.device.dut}',
            }

            # Refresh Device
            self.device.refresh()

            # Finish Time
            historic_self_test_logs_finish_time, historic_self_test_logs_duration = datetime.now(), str(datetime.now() - historic_self_test_logs_start_time)

            # Store Logs
            self.report['test']['smart_self_test_logs'].update({
                'logs': self.device.smart_self_tests
            })

            # Check if any self-test log matches the criteria
            if any('status' in log and 'passed' in log['status'] and not log['status']['passed'] for log in self.device.smart_self_tests):
                # Set Grade to F
                self.grade = "F"

                # Set Certified False
                self.is_certified_for_reuse = False

                # Set Certified False
                self.update_grade.emit("F")
                self.update_result.emit("FAIL")
                self.update_message.emit(f"Grading Complete - Historic failed Self-test log found - FAIL")
                self.update_comments.emit(f"Historic failed Self-test found in Logs. Not Certified for Reuse.")

                # Update Style
                self.update_progress.emit(100)
                self.update_progress_style.emit(failed_progress_bar)
                self.update_result_style.emit(failed_badge)
                self.update_grade_style.emit(failed_badge)

                # Update Report
                self.report['test']['smart_self_test_logs'].update({
                    'finished': historic_self_test_logs_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
                    'duration': historic_self_test_logs_duration,
                    'value': self.device.reallocated_sectors,
                    'result': "Fail",
                    'remarks': f"Historic Failed Self-test found in Logs."
                })

                # Update Status
                self.report['status']['result'] = "Fail"
                self.report['status']['remarks'] = f"Historic Failed Self-test found in Logs."

                # Raise Exception
                raise SMARTHistoricSelfTestFail('Historic Failed Self-test found in Logs.')

        # If SCSI Device
        if self.device.is_scsi:
            # Skip if none-logged
            if self.device.smart_self_tests == "No Self Tests Logged":
                # Return
                return

            # Emit
            self.update_state.emit("Testing")

            # Report
            self.report['test']['smart_self_test_logs'] = {
                'name': "S.M.A.R.T Self-test Log Analysis",
                'description': "Historic S.M.A.R.T Self-test Log analysis.",
                'started': historic_self_test_logs_start_time.strftime("%d/%m/%Y %H:%M:%S"),
                'finished': '',
                'duration': '',
                'threshold': "Must contain no failed Self-tests",
                'value': '',
                'result': '',
                'logs': '',
                'toolkit': f'smartctl',
                'command': f'smartctl --xall {self.device.dut}',
            }

            # Refresh Device
            self.device.refresh()

            # Finish Time
            historic_self_test_logs_finish_time, historic_self_test_logs_duration = datetime.now(), str(datetime.now() - historic_self_test_logs_start_time)

            # Store Logs
            self.report['test']['smart_self_test_logs'].update({
                'logs': self.device.smart_self_tests
            })

            # Check if any self-test log matches the criteria
            if any('result' in log and log['result']['string'] != 'Completed' for log in self.device.smart_self_tests):
                # Set Grade to F
                self.grade = "F"

                # Set Certified False
                self.is_certified_for_reuse = False

                # Set Certified False
                self.update_grade.emit("F")
                self.update_result.emit("FAIL")
                self.update_message.emit(f"Grading Complete - Historic failed Self-test log found - FAIL")
                self.update_comments.emit(f"Historic failed Self-test found in Logs. Not Certified for Reuse.")

                # Update Style
                self.update_progress.emit(100)
                self.update_progress_style.emit(failed_progress_bar)
                self.update_result_style.emit(failed_badge)
                self.update_grade_style.emit(failed_badge)

                # Update Report
                self.report['test']['smart_self_test_logs'].update({
                    'finished': historic_self_test_logs_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
                    'duration': historic_self_test_logs_duration,
                    'value': self.device.reallocated_sectors,
                    'result': "Fail",
                    'remarks': f"Historic Failed Self-test found in Logs."
                })

                # Update Status
                self.report['status']['result'] = "Fail"
                self.report['status']['remarks'] = f"Historic Failed Self-test found in Logs."

                # Raise Exception
                raise SMARTHistoricSelfTestFail('Historic Failed Self-test found in Logs.')

        # Finish Time
        historic_self_test_logs_finish_time, historic_self_test_logs_duration = datetime.now(), str(datetime.now() - historic_self_test_logs_start_time)

        # Update Report
        self.report['test']['smart_self_test_logs'].update({
            'finished': historic_self_test_logs_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
            'duration': historic_self_test_logs_duration,
            'value': self.device.reallocated_sectors,
            'result': "Fail",
            'remarks': f"Historic Failed Self-test found in Logs.."
        })

    def check_smart_short_self_test_status(self):
        """
        Check S.M.A.R.T Short Self-test Status
        """

        # Emit
        self.update_state.emit("Self-test")

        # Start Time
        smart_self_test_status_start_time = datetime.now()

        # Report
        self.report['test']['smart_self_test'] = {
            'name': "S.M.A.R.T Short Self-test Status",
            'description': "S.M.A.R.T Short Self-test Status",
            'started': smart_self_test_status_start_time.strftime("%d/%m/%Y %H:%M:%S"),
            'finished': '',
            'duration': '',
            'threshold': 'Must Pass',
            'value': '',
            'result': '',
            'logs': '',
            'toolkit': f'smartctl',
            'command': f'smartctl --test=short {self.device.dut}',
        }

        # Self Test
        self_test = self.device.execute_smart_short_self_test()

        # If Return Code is not 0
        if self_test.return_code != 0:
            print(self_test.return_code)
            print(self_test.get_output())
            print(self_test.get_errors())

            # Set Grade to F
            self.grade = "F"

            # Set Certified False
            self.is_certified_for_reuse = False

            # Set Certified False
            self.update_grade.emit("F")
            self.update_result.emit("FAIL")
            self.update_message.emit(f"Grading Complete - S.M.A.R.T Short Self-test failed - FAIL")
            self.update_comments.emit(f"S.M.A.R.T Self-test failed. Not Certified for Reuse.")

            # Update Style
            self.update_progress.emit(100)
            self.update_progress_style.emit(failed_progress_bar)
            self.update_result_style.emit(failed_badge)
            self.update_grade_style.emit(failed_badge)

            # Finish Time
            smart_self_test_status_finish_time, smart_self_test_status_duration = datetime.now(), str(datetime.now() - smart_self_test_status_start_time)

            # Update Report
            self.report['test']['smart_self_test'].update({
                'finished': smart_self_test_status_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
                'duration': smart_self_test_status_duration,
                'value': "Fail",
                'result': "Fail",
                'remarks': "S.M.A.R.T Short Self-test failed. Self-test must pass for CDI certification."
            })

            # Update Status
            self.report['status']['result'] = "Fail"
            self.report['status']['remarks'] = f"S.M.A.R.T Short Self-test failed."

            # Raise Exception
            raise SMARTSelfTestFail('S.M.A.R.T Short Self-test failed.')

        # Set Short Self Test
        self_test_type = "short"

        # Set Durations
        duration = total_duration = 120

        # Loop for Duration
        for i in range(duration, 0, -1):
            # Calculate Percent
            percent = int(100 - (i / total_duration * 100))

            # Set Message
            message = f"Testing - S.M.A.R.T Self Test - {self_test_type.title()} - {percent} % - {str(timedelta(seconds=duration))}"

            # Decrement Counter
            duration -= 1

            # Emit
            self.update_progress.emit(percent)
            self.update_message.emit(message)

            # Sleep
            self.sleep(1)

        # Then
        else:
            # Emit
            self.update_message.emit(f"Testing - S.M.A.R.T Self Test - {self_test_type.title()} - 100 % - 0:00:00")
            self.update_progress.emit(100)

        # Finish Time
        smart_self_test_status_finish_time, smart_self_test_status_duration = datetime.now(), str(datetime.now() - smart_self_test_status_start_time)

        # Store Logs
        self.report['test']['smart_self_test_logs'].update({
            'logs': self.device.smart_self_tests
        })

        # Update Report
        self.report['test']['smart_self_test'].update({
            'finished': smart_self_test_status_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
            'duration': smart_self_test_status_duration,
            'value': "Pass",
            'result': "Pass",
            'remarks': "S.M.A.R.T Short Self-test passed."
        })

        # Emit
        self.update_message.emit("S.M.A.R.T Short Self-test passed")

        # Go Idle
        self.go_idle(f"S.M.A.R.T {self_test_type.title()} Self-test", 10)

    def check_smart_vendor_self_test_status(self):
        """
        Check S.M.A.R.T Vendor-specific Self-test Status
        """

        # Emit
        self.update_state.emit("Self-test")

        # Start Time
        smart_self_test_status_start_time = datetime.now()

        # Report
        self.report['test']['smart_vendor_self_test'] = {
            'name': "S.M.A.R.T Vendor-specific Self-test Status",
            'description': "S.M.A.R.T Vendor-specific Self-test Status",
            'started': smart_self_test_status_start_time.strftime("%d/%m/%Y %H:%M:%S"),
            'finished': '',
            'duration': '',
            'threshold': 'Must Pass',
            'value': '',
            'result': '',
            'toolkit': f'smartctl',
            'command': f'smartctl --test=vendor,0xFF {self.device.dut}',
        }

        # S.M.A.R.T Vendor Specific Self-test
        vendor_self_test = self.device.execute_smart_vendor_self_test()

        # If Return Code is not 0
        if vendor_self_test.return_code != 0:
            # Set Grade to F
            self.grade = "F"

            # Set Certified False
            self.is_certified_for_reuse = False

            # Set Certified False
            self.update_grade.emit("F")
            self.update_result.emit("FAIL")
            self.update_message.emit(f"Grading Complete - S.M.A.R.T Vendor Self-test failed - FAIL")
            self.update_comments.emit(f"S.M.A.R.T Vendor Self-test failed. Not Certified for Reuse.")

            # Update Style
            self.update_progress.emit(100)
            self.update_progress_style.emit(failed_progress_bar)
            self.update_result_style.emit(failed_badge)
            self.update_grade_style.emit(failed_badge)

            # Finish Time
            smart_self_test_status_finish_time, smart_self_test_status_duration = datetime.now(), str(datetime.now() - smart_self_test_status_start_time)

            # Update Report
            self.report['test']['smart_self_test'].update({
                'finished': smart_self_test_status_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
                'duration': smart_self_test_status_duration,
                'value': "Fail",
                'result': "Fail",
                'remarks': "S.M.A.R.T Vendor Self-test failed. Self-test must pass for CDI certification."
            })

            # Update Status
            self.report['status']['result'] = "Fail"
            self.report['status']['remarks'] = f"S.M.A.R.T Vendor Self-test failed."

            # Raise Exception
            raise SMARTSelfTestFail('S.M.A.R.T Vendor Self-test failed.')

        # Set Short Self Test
        self_test_type = "vendor specific"

        # Set Durations
        duration = total_duration = 120

        # Loop for Duration
        for i in range(duration, 0, -1):
            # Calculate Percent
            percent = int(100 - (i / total_duration * 100))

            # Set Message
            message = f"Testing - S.M.A.R.T Self Test - {self_test_type.title()} - {percent} % - {str(timedelta(seconds=duration))}"

            # Decrement Counter
            duration -= 1

            # Emit
            self.update_progress.emit(percent)
            self.update_message.emit(message)

            # Sleep
            self.sleep(1)

        # Finished
        else:
            # Emit
            self.update_progress.emit(100)
            self.update_message.emit(f"Testing - S.M.A.R.T Self Test - {self_test_type.title()} - 100 % - 00:00:00")

        # Finish Time
        smart_self_test_status_finish_time, smart_self_test_status_duration = datetime.now(), str(datetime.now() - smart_self_test_status_start_time)

        # Store Logs
        self.report['test']['smart_self_test_logs'].update({
            'logs': self.device.smart_self_tests
        })

        # Update Report
        self.report['test']['smart_self_test'].update({
            'finished': smart_self_test_status_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
            'duration': smart_self_test_status_duration,
            'value': "Pass",
            'result': "Pass",
            'remarks': "S.M.A.R.T Vendor Self-test passed."
        })

        # Emit
        self.update_message.emit("S.M.A.R.T Vendor Self-test passed")

        # Go Idle
        self.go_idle(f"S.M.A.R.T {self_test_type.title()} Self-test", 10)

    def check_reallocated_sectors(self):
        """
        Check Reallocated Sectors
        """

        # If Reallocated Sectors are not None
        if self.device.reallocated_sectors is not None:
            # Emit
            self.update_state.emit("Testing")

            # Start Time
            reallocated_sectors_start_time = datetime.now()

            # Report
            self.report['test']['reallocated_sectors'] = {
                'name': "Reallocated Sectors",
                'description': "Reallocated Sectors check and analysis",
                'started': reallocated_sectors_start_time.strftime("%d/%m/%Y %H:%M:%S"),
                'finished': '',
                'duration': '',
                'threshold': CDI_MAXIMUM_REALLOCATED_SECTORS,
                'value': '',
                'result': '',
                'toolkit': f'smartctl',
                'command': f'smartctl --xall {self.device.dut}',
            }

            # Refresh Device
            self.device.refresh()

            # Finish Time
            reallocated_sectors_finish_time, reallocated_sectors_duration = datetime.now(), str(datetime.now() - reallocated_sectors_start_time)

            # If Reallocated Sectors exceeds CDI Maximum
            if self.device.reallocated_sectors > CDI_MAXIMUM_REALLOCATED_SECTORS:
                # Set Grade to F
                self.grade = "F"

                # Set Certified False
                self.is_certified_for_reuse = False

                # Set Certified False
                self.update_grade.emit("F")
                self.update_result.emit("FAIL")
                self.update_message.emit(f"Grading Complete - Too many Reallocated Sectors - Fail")
                self.update_comments.emit(f"Reallocated Sectors exceeds CDI threshold. Not Certified for Reuse.")

                # Update Style
                self.update_progress.emit(100)
                self.update_progress_style.emit(failed_progress_bar)
                self.update_result_style.emit(failed_badge)
                self.update_grade_style.emit(failed_badge)

                # Update Report
                self.report['test']['reallocated_sectors'].update({
                    'finished': reallocated_sectors_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
                    'duration': reallocated_sectors_duration,
                    'value': self.device.reallocated_sectors,
                    'result': "Fail",
                    'remarks': f"Reallocated Sectors value exceeds the CDI threshold of {CDI_MAXIMUM_REALLOCATED_SECTORS}."
                })

                # Update Status
                self.report['status']['result'] = "Fail"
                self.report['status']['remarks'] = f"Reallocated Sectors value exceeds the CDI threshold of {CDI_MAXIMUM_REALLOCATED_SECTORS}."

                # Raise Exception
                raise ReallocatedSectorsExceedsThreshold('Reallocated Sectors threshold exceeded')

            # Update Report
            self.report['test']['reallocated_sectors'].update({
                'finished': reallocated_sectors_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
                'duration': reallocated_sectors_duration,
                'value': self.device.reallocated_sectors,
                'result': "Pass",
                'remarks': f"Reallocated Sectors value is within threshold."
            })

            # Emit
            self.update_message.emit("Reallocated Sectors within threshold.")

    def check_pending_sectors(self):
        """
        Check Pending Sectors
        """

        # If Reallocated Sectors are not None
        if self.device.pending_sectors is not None:
            # Emit
            self.update_state.emit("Testing")

            # Start Time
            pending_sectors_start_time = datetime.now()

            # Report
            self.report['test']['pending_sectors'] = {
                'name': "Pending Sectors",
                'description': "Pending Sectors check and analysis",
                'started': pending_sectors_start_time.strftime("%d/%m/%Y %H:%M:%S"),
                'finished': '',
                'duration': '',
                'threshold': CDI_MAXIMUM_PENDING_SECTORS,
                'value': '',
                'result': '',
                'toolkit': f'smartctl',
                'command': f'smartctl --xall {self.device.dut}',
            }

            # Refresh Device
            self.device.refresh()

            # Finish Time
            pending_sectors_finish_time, pending_sectors_duration = datetime.now(), str(datetime.now() - pending_sectors_start_time)

            # If Pending Sectors
            if self.device.pending_sectors is not None:
                # If Pending Sectors exceeds CDI Maximum
                if self.device.pending_sectors > CDI_MAXIMUM_PENDING_SECTORS:
                    # Set Grade to F
                    self.grade = "F"

                    # Set Certified False
                    self.is_certified_for_reuse = False

                    # Set Certified False
                    self.update_grade.emit("F")
                    self.update_result.emit("FAIL")
                    self.update_message.emit(f"Grading Complete - Fail")
                    self.update_comments.emit(f"Pending Sectors exceeds Threshold. Not Certified for Reuse.")

                    # Update Style
                    self.update_result_style.emit(failed_badge)
                    self.update_grade_style.emit(failed_badge)
                    self.update_progress_style.emit(failed_progress_bar)

                    # Update Report
                    self.report['test']['pending_sectors'].update({
                        'finished': pending_sectors_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
                        'duration': pending_sectors_duration,
                        'value': self.device.pending_sectors,
                        'result': "Fail",
                        'remarks': f"Pending Sectors value exceeds the CDI threshold of {CDI_MAXIMUM_PENDING_SECTORS}."
                    })

                    # Update Status
                    self.report['status']['result'] = "Fail"
                    self.report['status']['remarks'] = f"Pending Sectors value exceeds the CDI threshold of {CDI_MAXIMUM_PENDING_SECTORS}."

                    # Raise
                    raise PendingSectorsExceedsThreshold('Pending Sectors exceeds Threshold.')

                # Update Report
                self.report['test']['pending_sectors'].update({
                    'finished': pending_sectors_finish_time.strftime("%d/%m/%Y %H:%M:%S"),
                    'duration': pending_sectors_duration,
                    'value': self.device.pending_sectors,
                    'result': "Pass",
                    'remarks': f"Pending Sectors value is within threshold."
                })

                # Emit
                self.update_message.emit("Pending Sectors within threshold")

    def check_start_stop_count(self):
        # Emit
        self.update_state.emit("Testing")

        # Start Time
        start_stop_count_start_time = datetime.now()

        # Report
        self.report['test']['start_stop_count'] = {
            'name': "Start/Stop Count",
            'description': "Start/Stop Count check and analysis",
            'started': start_stop_count_start_time.strftime("%d/%m/%Y %H:%M:%S"),
            'finished': '',
            'duration': '',
            'threshold': "Must not exceed vendor limit",
            'value': '',
            'result': '',
            'toolkit': f'smartctl',
            'command': f'smartctl --xall {self.device.dut}',
        }

        # Refresh Device
        self.device.refresh()

        # Finish Time
        start_stop_count_finish_time, start_stop_count_duration = datetime.now(), str(datetime.now() - start_stop_count_start_time)

        # If Reallocated Sectors exceeds CDI Maximum
        if self.device.start_stop_count > 10:
            print("OOPS")


class Scanner(QThread):
    """
    Scan Thread
    """

    # Signals
    set_devices = Signal(object)
    start_spinner = Signal(bool)
    stop_spinner = Signal(bool)

    def __init__(self, configuration):
        """
        Constructor
        @param configuration:
        """

        # Initialize
        super().__init__()

        # Set Configuration
        self.configuration = configuration

        # Set Devices List
        self.devices = list()

    def run(self) -> bool:
        """
        Run
        """

        # Start Spinner
        self.start_spinner.emit(True)

        # Get Devices
        self.devices = Devices(
            ignore_ata=self.configuration.get_boolean('ignore', 'ignore_ata'),
            ignore_nvme=self.configuration.get_boolean('ignore', 'ignore_nvme'),
            ignore_scsi=self.configuration.get_boolean('ignore', 'ignore_scsi'),
            ignore_removable=self.configuration.get_boolean('ignore', 'ignore_usb'),
        )

        # Set Devices
        self.set_devices.emit(self.devices)

        # Stop Spinner
        self.stop_spinner.emit(True)

        # Return True
        return True
