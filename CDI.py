"""
Circular Drive Initiative

@language    Python 3.12
@framework   PySide 6
@version     0.0.1
"""

# Modules
import argparse

# PySide6
from PySide6.QtCore import Slot, QTime, QDate
from PySide6.QtGui import Qt, QPixmap, QAction, QCursor, QBrush
from PySide6.QtWidgets import QMainWindow, QSplashScreen, QMenu, QTableWidgetItem, QProgressBar

# Classes
from classes.configuration import Configuration
from classes.exceptions import *
from classes.threads import *
from classes.widgets import *
from constants import *

# User Interface
from ui import Ui_CDIGradingTool


class CDIGradingTool(QMainWindow):
    """
    ---------------------------------------------------------------------
    CDI Grading Tool Class
    ---------------------------------------------------------------------
    Primary PySide QApplication - QMainWindow
    ---------------------------------------------------------------------
    """

    # Set Arguments List
    arguments = list()

    # Set Scan Dict
    scans = {}

    # Set Thread Dict
    threads = {}

    # Set Control List Dict
    control_list = {}

    # Set Launch Methods Dict
    launch_methods = {}

    def __init__(self):
        """
        Constructor
        """

        # Initialize Main Window
        super(CDIGradingTool, self).__init__()

        # Create Parser
        self.parser: argparse.ArgumentParser = argparse.ArgumentParser()

        # Parse Arguments
        self.parse_arguments()

        # Load Configuration
        self.configuration: Configuration = self.load_configuration()

        # Load User Interface
        self.ui: Ui_CDIGradingTool = self.load_user_interface()

        # Load Splashscreen
        self.splashscreen: QSplashScreen = self.load_splashscreen()

        # Instantiate Splashscreen Progress Bar
        self.splashscreen_progress_bar: QProgressBar = QProgressBar(self.splashscreen)

        # Set Spinner
        self.spinner = Spinner(self)

        # Set Scanner
        self.scanner = Scanner(self.configuration)
        self.scanner.start_spinner.connect(self.spinner.start)
        self.scanner.stop_spinner.connect(self.spinner.stop)

        # Time
        self.timer = QTimer(self)

        # Start Timer
        self.date_time_timer()

    """
    Application Arguments
    """

    def parse_arguments(self):
        """
        Parse Arguments
        :return: Arguments List
        """

        # Add Arguments
        self.parser.add_argument('--verbose', action='store_true', help='launch in Verbose mode', default=False)
        self.parser.add_argument('--auto-grade', action='store_true', help='auto-grade all devices', default=False)
        self.parser.add_argument('--auto-shutdown', action='store_true', help='auto-shutdown after all jobs complete', default=False)
        self.parser.add_argument('--only-ata', action='store_true', help='scan for ATA devices only', default=False)
        self.parser.add_argument('--only-nvme', action='store_true', help='scan for NVMe devices only', default=False)
        self.parser.add_argument('--only-scsi', action='store_true', help='scan for SCSI devices only', default=False)
        self.parser.add_argument('--only-usb', action='store_true', help='scan for USB devices only', default=False)
        self.parser.add_argument('--ignore-ata', action='store_true', help='ignore ATA devices when scanning',  default=False)
        self.parser.add_argument('--ignore-nvme', action='store_true', help='ignore NVMe devices when scanning', default=False)
        self.parser.add_argument('--ignore-scsi', action='store_true', help='ignore SCSI devices when scanning', default=False)
        self.parser.add_argument('--ignore-usb', action='store_true', help='ignore USB devices when scanning', default=False)

        # Parse Arguments
        self.arguments = self.parser.parse_args()

    """
    Application Configuration
    """

    def load_configuration(self):
        """
        Load Configuration
        :return:
        """

        # Load Configuration
        self.configuration = Configuration(configuration_file)

        # Return Configuration
        return self.configuration

    """
    Application Setup
    """

    def do_initial_setup(self):
        """
        Setup CDI Grading Tool
        :return:
        """

        # Show Splashscreen
        self.show_splashscreen()

        # Create Launch Methods
        self.launch_methods = {
            # Get and Set Devices
            'do_initial_get_and_set_devices_table': {
                'message': "Getting and Setting Devices",
                'method': self.do_initial_get_and_set_devices_table,
            },
        }

        # Loop Launch Methods
        for key, values in self.launch_methods.items():
            # Execute Method
            values['method']()

        # Load Signals and Slots
        self.load_signals_and_slots()

        # End Splashscreen
        self.close_splashscreen()

        # Launch
        self.launch(maximized=True)

    """
    Application Actions
    """

    def launch(self, normal: bool = False, minimized: bool = False, maximized: bool = False, fullscreen: bool = False, frameless: bool = False) -> bool:
        """
        Launch the User Interface
        :param normal: launch in normal mode
        :param minimized: launch in minimized mode
        :param maximized: launch in maximized mode
        :param frameless: launch in frameless mode
        :param fullscreen: launch in fullscreen mode
        :return: CDI Grading Tool launched in selected mode
        :return: bool
        """

        # If Frameless
        if frameless:
            # Set Window Flag to Frameless
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        # If Normal
        if normal:
            # Show Normal
            self.showNormal()

        # If Minimized
        if minimized:
            # Show Minimized
            self.showMinimized()

        # If Maximized
        elif maximized:
            # Show Maximized
            self.showMaximized()

        # If Full Screen
        elif fullscreen:
            # Show Full Screen
            self.showFullScreen()

        # Else
        else:
            # Show
            self.show()

        # Return
        return True

    def shutdown(self, auto_shutdown: bool = False):
        """
        Shutdown
        @param auto_shutdown: whether to bypass the prompt and shutdown immediately
        """

        # Close
        self.close()

        # If Auto Shutdown
        if auto_shutdown:
            # Execute Shutdown
            return subprocess.run(shutdown_now)

        # Prepare Shutdown Prompt
        shutdown_prompt = PowerDialog(self, "Exit", "Are you sure you want to exit?")

        # Execute
        shutdown_prompt.exec()

    """
    Application User Interface
    """

    def load_user_interface(self):
        """
        Load User Interface
        """

        # Set UI
        self.ui = Ui_CDIGradingTool()

        # Load User Interface
        self.ui.setupUi(self)

        # Return UI
        return self.ui

    def load_splashscreen(self):
        """
        Load the Splashscreen
        """

        # Instantiate Splashscreen
        self.splashscreen = QSplashScreen()

        # Return Splashscreen
        return self.splashscreen

    def show_splashscreen(self):
        """
        Show the Splashscreen
        """

        # Get Dimensions
        height, width, ratio = (
            splashscreen_height,
            splashscreen_width,
            keep_aspect_ratio
        )

        # Set Splashscreen Image
        splashscreen_image = QPixmap(splashscreen).scaled(height, width, ratio)

        # Set Maximum
        self.splashscreen_progress_bar.setMaximum(percent_100)

        # Set Geometry
        self.splashscreen_progress_bar.setGeometry(percent_25, height - percent_50, width - percent_50, percent_25)

        # Set Image
        self.splashscreen.setPixmap(splashscreen_image)

        # Show Splash Screen
        self.splashscreen.showNormal()

    def close_splashscreen(self):
        """
        Close the Splashscreen
        """

        # Hide Splash Screen
        self.splashscreen.finish(self)

    def date_time_timer(self):
        """
        Date/Time Timer
        """

        # Time Signal
        self.timer.timeout.connect(self.update_date_and_time)

        # Start Timer
        self.timer.start(1000)

        # Update Time
        self.update_date_and_time()

    def update_date_and_time(self):
        """
        Update Date and Time
        """

        # Current Time
        current_time = QTime.currentTime()
        current_date = QDate.currentDate()

        # Format Strings
        time_text = current_time.toString("hh:mm:ss")
        date_text = current_date.toString("yyyy-MM-dd")

        # Set Text and Style
        time_style = 'color: black; font-size: 16px;'
        date_style = 'color: black; font-size: 12px;'

        # Set Time Label Text
        self.ui.time_label.setText(f'<span style="{time_style}">{time_text}</span><br><span style="{date_style}">{date_text}</span>')

    """
    Application Signals
    """

    def load_signals_and_slots(self):
        """
        Load Signals and Slots
        :return:
        """

        """ DEVICES """

        # Device Refresh Signal
        self.ui.refresh_devices_button.clicked.connect(self.refresh_devices_table)

        # Set Devices Filter Signal
        self.ui.filter_button.clicked.connect(self.filter_devices_table)

        # Set Devices Search Signal
        self.ui.devices_search_field.textChanged.connect(self.search_devices_table)

        # Set Devices Process All Signal
        self.ui.process_all_button.clicked.connect(self.process_all_devices)

        # Set Devices Process Processed Signal
        self.ui.process_selected_button.clicked.connect(self.process_selected_devices)

        # Set Devices Table Context Menu Policy
        self.ui.devices_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Set Devices Table Custom Context Menu
        self.ui.devices_table.customContextMenuRequested.connect(self.show_devices_context_menu)

        """ JOBS """

        # Set Job Search Signal
        self.ui.jobs_search_field.textChanged.connect(self.search_jobs_table)

    @Slot()
    def update_console(self):
        # Todo
        pass

    @Slot()
    def update_control_list(self):
        # Todo
        pass

    @Slot()
    def update_device_state(self):
        # Todo
        pass

    @Slot()
    def raise_error_dialog(self):
        # Todo
        pass

    """
    Application Menus
    """

    @Slot()
    def setup_default_devices_menu(self, menu):
        """
        Propagate Default Devices Menu Options
        :param menu:
        :return:
        """

        # Default Menu Command List
        default_commands = {
            # Blink
            'blink': {
                'name': "Blink LED",
                'icon': QIcon(f"{app_path}/assets/images/blink.png"),
                # 'method': self.blink_selected_device, # TODO - add blink logic
                'shortcut': "Ctrl+B"
            },
            # Hexview
            'hexview': {
                'name': "Hexview",
                'icon': QIcon(f"{app_path}/assets/images/hexview.png"),
                # 'method': self.hexview_selected_device, # TODO - add hexview logic
                'shortcut': "Ctrl+H"
            },
        }

        # Loop ATA Tools Commands
        for key, values in default_commands.items():
            # Set QAction
            action = QAction(values['icon'], values['name'], self)

            # Connect Signal
            # action.triggered.connect(values['method']) # TODO - Connect the signal to the slot

            # If Shortcut
            if values['shortcut'] is not None:
                # Set Shortcut
                action.setShortcut(values['shortcut'])

            # Add Action
            menu.addAction(action)

        # Else
        else:
            # Add Seperator
            menu.addSeparator()

        # Return Menu
        return menu

    @Slot()
    def setup_default_jobs_menu(self, menu):
        """
        Setup Default Jobs Context Menu
        :param menu:
        :return:
        """

        # Default Menu Command List
        default_commands = {
            # Blink
            'blink': {
                'name': "Blink LED",
                'icon': QIcon(f'{app_path}/images/blink.png'),
                # 'method': self.blink_selected_device,
                'shortcut': "Ctrl+B"
            },
            # Hexview
            'hexview': {
                'name': "Hexview",
                'icon': QIcon(f'{app_path}/images/hexview.png'),
                # 'method': self.hexview_selected_device,
                'shortcut': "Ctrl+H"
            },
        }

        # Loop ATA Tools Commands
        for key, values in default_commands.items():
            # Set QAction
            action = QAction(values['icon'], values['name'], self)

            # Connect Signal
            action.triggered.connect(values['method'])

            # If Shortcut
            if values['shortcut'] is not None:
                # Set Shortcut
                action.setShortcut(values['shortcut'])

            # Add Action
            menu.addAction(action)

        # Then
        else:
            # Add Seperator
            menu.addSeparator()

        # Return Menu
        return menu

    @Slot()
    def setup_ata_menu(self):
        """
        Propagate ATA Menu
        """

        # Create ATA Menu
        ata_menu = QMenu(self)
        ata_menu.setFont(QFont("Arial", 10))

        # Setup Default Items
        self.setup_default_devices_menu(ata_menu)

        # Set Icons
        command_icon = QIcon(f'{images_path}/command.png', )

        """
        ATA Tools
        """

        # ATA Tool List
        ata_tools = {
            # HDParm
            'hdparm': {
                'name': "View HDParm Information",
                'icon': command_icon,
                'method': self.show_hdparm_as_text,
            },
            # HDSentinel
            'hdsentinel': {
                'name': "View HDSentinel Information",
                'icon': command_icon,
                'method': self.show_hdsentinel_as_text,
            },
            # SeaTools
            'seatools': {
                'name': "View SeaTools Information",
                'icon': command_icon,
                'method': self.show_seatools_as_text,
            },
            # Sedutil
            'sedutil': {
                'name': "View Sedutil Information",
                'icon': command_icon,
                'method': self.show_sedutil_as_text,
            },
            # Smartctl
            'smartctl': {
                'name': "View Smartctl Information",
                'icon': command_icon,
                'method': self.show_smartctl_as_text,
            },
        }

        # Loop ATA Tools Commands
        for key, values in ata_tools.items():
            # Set QAction
            action = QAction(values['icon'], values['name'], self)

            # Connect Signal
            action.triggered.connect(values['method'])

            # Add Action
            ata_menu.addAction(action)

        # Else
        else:
            # Add Seperator
            ata_menu.addSeparator()

        # S.M.A.R.T Commands Menu
        smart_commands_menu = ata_menu.addMenu(command_icon, "S.M.A.R.T Commands")
        smart_commands_menu.setFont(QFont("Arial", 10))

        # S.M.A.R.T Commands
        smart_commands = {
            # Show S.M.A.R.T Health
            'view_smart_health': {
                'name': "View S.M.A.R.T Health",
                'icon': command_icon,
                # 'method': self.show_smartctl_health, # TODO - create show smartctl health logic/widget
            },
            # Show S.M.A.R.T Information
            'view_smart_information': {
                'name': "View S.M.A.R.T Information",
                'icon': command_icon,
                # 'method': self.show_smartctl_information, # TODO - create show smartctl information logic/widget
            },
            # Show S.M.A.R.T Attributes
            'view_smart_attributes': {
                'name': "View S.M.A.R.T Attributes",
                'icon': command_icon,
                # 'method': self.show_smartctl_attributes, # TODO - create show smartctl attributes logic/widget
            },
            # Show S.M.A.R.T Attributes
            'view_smart_self_test_logs': {
                'name': "View S.M.A.R.T Self Test Logs",
                'icon': command_icon,
                # 'method': self.show_smartctl_self_test_log, # TODO - create show smartctl self-test logs logic/widget
            },
            # Show S.M.A.R.T Attributes
            'view_smart_error_logs': {
                'name': "View S.M.A.R.T Error Logs",
                'icon': command_icon,
                # 'method': self.show_smartctl_error_log, # TODO - create show smartctl information logic/widget
            },
        }

        # Loop Capacity Commands
        for key, values in smart_commands.items():
            # Set QAction
            action = QAction(values['icon'], values['name'], self)

            # Connect Signal
            # action.triggered.connect(values['method']) # TODO - connect signal to slot

            # Add Action
            smart_commands_menu.addAction(action)

        # Return ATA Menu
        return ata_menu

    @Slot()
    def show_devices_context_menu(self):
        """
        Show Context Menu Helper
        """

        # If no row selected
        if self.ui.devices_table.currentRow() == -1:
            # Return
            return

        # Select Current Row
        self.ui.devices_table.selectRow(self.ui.devices_table.currentRow())

        # Define Context Menu
        menu = QMenu(self)

        # Set Context Menu Font
        menu.setFont(QFont("Arial", 10))

        # Get Transport Protocol
        transport_protocol = self.ui.devices_table.cellWidget(self.ui.devices_table.currentRow(), 4).text()

        # If ATA
        if transport_protocol == "ATA":
            # Propagate ATA Context Menu
            self.setup_ata_menu().exec(QCursor.pos())

        # If NVMe
        elif transport_protocol == "NVMe":
            # Propagate NVMe Context Menu
            self.setup_ata_menu().exec(QCursor.pos())

        # If SCSI
        elif transport_protocol == "SCSI":
            # Propagate SCSI Context Menu
            self.setup_ata_menu().exec(QCursor.pos())

        # If USB
        elif transport_protocol == "USB":
            # Propagate Removable Context Menu
            self.setup_ata_menu().exec(QCursor.pos())

        # Else
        else:
            # Load Default Context Menu
            menu.exec(QCursor.pos())

    @Slot()
    def show_jobs_context_menu(self):
        """
        Show Jobs Context Menu
        :return:
        """

        # Check if a row is selected
        if self.ui.jobs_table.currentRow() == -1:
            # Return
            return

        # Select Row
        self.ui.jobs_table.selectRow(self.ui.jobs_table.currentRow())

        # Define Context Menu
        jobs_menu = QMenu(self)

        # Set Font
        jobs_menu.setFont(QFont("Arial", 10))

        # Setup Default Items
        self.setup_default_jobs_menu(jobs_menu)

        # Set Icons
        command_icon = QIcon(f"{images_path}/command.png")

        # Jobs Command List
        jobs_commands = {
            # Cancel
            'cancel': {
                'name': "Cancel",
                'icon': command_icon,
                # 'method': self.cancelled, # TODO - create logic for semaphore acquisition and cancelling grading
            },
        }

        # Loop ATA Tools Commands
        for key, values in jobs_commands.items():
            # Set QAction
            action = QAction(values['icon'], values['name'], self)

            # Connect Signal
            action.triggered.connect(values['method'])

            # Add Action
            jobs_menu.addAction(action)

        # Then
        else:
            # Add Seperator
            jobs_menu.addSeparator()

        # Return Context Menu
        return jobs_menu.exec(QCursor.pos())

    """
    Devices
    """

    @Slot()
    def do_initial_get_and_set_devices_table(self) -> bool:
        """
        Do Initial Get and Set of Devices
        :return: bool
        """

        # Reset Devices Table
        self.purge_devices_table()

        # Purge Device Search Field
        self.purge_devices_search()

        # Connect Signals
        self.scanner.set_devices.connect(self.set_devices_table)

        # Start Thread
        self.scanner.start()

        # Return
        return True

    @Slot()
    def get_all_devices_from_table(self):
        """
        Get All Devices from Devices Table
        @return list:
        """

        # Process List
        devices_to_process = list()

        # Get Total Devices
        total_devices = self.ui.devices_table.rowCount()

        # If no Devices
        if total_devices == 0:
            # Raise Exception
            raise NoDevicesDetectedException("No Devices detected")

        # Loop through all rows
        for row in range(total_devices):
            # Get Device Properties
            device_dict = {
                '#': self.ui.devices_table.item(row, 0).text(),
                'dut': self.ui.devices_table.item(row, 1).text(),
                'state': self.ui.devices_table.item(row, 2).text(),
                'type': self.ui.devices_table.cellWidget(row, 3).text(),
                'protocol': self.ui.devices_table.cellWidget(row, 4).text(),
                'vendor': self.ui.devices_table.item(row, 5).text(),
                'model': self.ui.devices_table.item(row, 6).text(),
                'serial': self.ui.devices_table.item(row, 7).text(),
                'firmware': self.ui.devices_table.item(row, 8).text(),
                'capacity': self.ui.devices_table.item(row, 9).text(),
                'sector_size': self.ui.devices_table.item(row, 10).text(),
                'power_on_hours': self.ui.devices_table.item(row, 11).text(),
                'smart_status': self.ui.devices_table.cellWidget(row, 12).text(),
                'grade': self.ui.devices_table.cellWidget(row, 13).text(),
                'row': row
            }

            # Append to Process List
            devices_to_process.append(device_dict)

        # Return Devices
        return devices_to_process

    @Slot()
    def get_selected_device_from_table(self):
        """
        Get Selected Device
        @return list:
        """

        # Get Selected Rows
        selected_rows = self.ui.devices_table.selectionModel().selectedRows()

        # Loop Selected Rows
        for index in selected_rows:
            # Get Device Properties
            device = {
                '#': self.ui.devices_table.item(index.row(), 0).text(),
                'dut': self.ui.devices_table.item(index.row(), 1).text(),
                'state': self.ui.devices_table.item(index.row(), 2).text(),
                'type': self.ui.devices_table.cellWidget(index.row(), 3).text(),
                'protocol': self.ui.devices_table.cellWidget(index.row(), 4).text(),
                'vendor': self.ui.devices_table.item(index.row(), 5).text(),
                'model': self.ui.devices_table.item(index.row(), 6).text(),
                'serial': self.ui.devices_table.item(index.row(), 7).text(),
                'firmware': self.ui.devices_table.item(index.row(), 8).text(),
                'capacity': self.ui.devices_table.item(index.row(), 9).text(),
                'sector_size': self.ui.devices_table.item(index.row(), 10).text(),
                'poh': self.ui.devices_table.item(index.row(), 11).text(),
                'smart_status': self.ui.devices_table.cellWidget(index.row(), 12).text(),
                'grade': self.ui.devices_table.cellWidget(index.row(), 13).text(),
                'row': index.row()
            }

            # Return Devices
            return device

    @Slot()
    def get_selected_devices_from_table(self):
        """
        Get Selected Devices
        @return int | list:
        """

        # Get Selected Rows
        selected_rows = self.ui.devices_table.selectionModel().selectedRows()

        # Process List
        devices_to_process = list()

        # Loop Selected Rows
        for index in selected_rows:
            # Get Device Properties
            device = {
                '#': self.ui.devices_table.item(index.row(), 0).text(),
                'dut': self.ui.devices_table.item(index.row(), 1).text(),
                'state': self.ui.devices_table.item(index.row(), 2).text(),
                'type': self.ui.devices_table.cellWidget(index.row(), 3).text(),
                'protocol': self.ui.devices_table.cellWidget(index.row(), 4).text(),
                'vendor': self.ui.devices_table.item(index.row(), 5).text(),
                'model': self.ui.devices_table.item(index.row(), 6).text(),
                'serial': self.ui.devices_table.item(index.row(), 7).text(),
                'firmware': self.ui.devices_table.item(index.row(), 8).text(),
                'capacity': self.ui.devices_table.item(index.row(), 9).text(),
                'sector_size': self.ui.devices_table.item(index.row(), 10).text(),
                'poh': self.ui.devices_table.item(index.row(), 11).text(),
                'smart_status': self.ui.devices_table.cellWidget(index.row(), 12).text(),
                'grade': self.ui.devices_table.cellWidget(index.row(), 13).text(),
                'row': index.row()
            }

            # Append to Process List
            devices_to_process.append(device)

        # Return Devices
        return devices_to_process

    @Slot()
    def process_all_devices(self):
        """
        Process All Devices in Devices Table
        :return:
        """

        # Execute Prompt, if not accepted, return
        if not GenericPromptDialog(self).exec() == QDialog.DialogCode.Accepted:
            # Return
            return

        # Get All Devices from Device Table
        devices = self.get_all_devices_from_table()

        # Create Jobs
        for device in devices:
            # If DUT isn't in Control List
            if device['dut'] not in self.control_list:
                # Loop Jobs Table Rows
                for row in range(self.ui.jobs_table.rowCount() - 1, -1, -1):
                    # Get DUT
                    dut = self.ui.jobs_table.item(row, 0).text()

                    # If DUT match
                    if dut == device['dut']:
                        # Remove Row from Jobs Table
                        self.ui.jobs_table.removeRow(row)

            # Set Status
            device_status = QTableWidgetItem("Testing")
            device_status.setTextAlignment(align_center)
            device_status.setForeground(QBrush(QColor('red')))
            device_status.setIcon(QIcon(QPixmap(f'{app_path}/images/warning.png')))

            # Set Device Status
            self.ui.devices_table.setItem(device.get('row'), 2, device_status)

            # Set Row
            row = self.ui.jobs_table.rowCount()

            # Insert Row
            self.ui.jobs_table.insertRow(row)

            # Table Objects
            dut = QTableWidgetItem(device.get('dut'))
            model = QTableWidgetItem(device.get('model'))
            serial = QTableWidgetItem(device.get('serial'))
            capacity = QTableWidgetItem(device.get('capacity'))
            state = QTableWidgetItem("Starting")
            comments = QTableWidgetItem()

            # Grade Label
            grade = QLabel(grade_u)
            grade.setStyleSheet(pending_badge)
            grade.setAlignment(align_center)

            # Result Label
            result = QLabel("ONGOING")
            result.setStyleSheet(pending_badge)
            result.setAlignment(align_center)

            # Progress Bar
            progress_bar = QProgressBar()
            progress_bar.setValue(0)
            progress_bar.setRange(0, 100)
            progress_bar.setStyleSheet(pending_progress_bar)

            # Insert Cell Items
            self.ui.jobs_table.setItem(row, 0, dut)
            self.ui.jobs_table.setItem(row, 1, model)
            self.ui.jobs_table.setItem(row, 2, serial)
            self.ui.jobs_table.setItem(row, 3, capacity)
            self.ui.jobs_table.setItem(row, 4, state)
            self.ui.jobs_table.setCellWidget(row, 5, progress_bar)
            self.ui.jobs_table.setCellWidget(row, 6, result)
            self.ui.jobs_table.setCellWidget(row, 7, grade)
            self.ui.jobs_table.setItem(row, 8, comments)

            # Hide Grade Column
            self.ui.jobs_table.hideColumn(7)

            # Create Grading Thread
            grading_thread = Grading(device)
            grading_thread.finished.connect(self.finished)
            grading_thread.terminated.connect(self.terminated)
            grading_thread.raise_error_dialog.connect(self.raise_error_dialog)
            grading_thread.update_console.connect(self.update_console)
            grading_thread.update_control_list.connect(self.update_control_list)
            grading_thread.update_device_state.connect(self.update_device_state)
            grading_thread.update_progress.connect(progress_bar.setValue)
            grading_thread.update_message.connect(progress_bar.setFormat)
            grading_thread.update_progress_style.connect(progress_bar.setStyleSheet)
            grading_thread.update_state.connect(state.setText)
            grading_thread.update_result.connect(result.setText)
            grading_thread.update_result_style.connect(result.setStyleSheet)
            grading_thread.update_grade.connect(grade.setText)
            grading_thread.update_grade_style.connect(grade.setStyleSheet)
            grading_thread.update_comments.connect(comments.setText)
            grading_thread.start()

            # Add to Control List
            self.control_list[device.get('dut')] = dict(
                id=None,
                dut=device.get('dut'),
                model=device.get('model'),
                serial=device.get('serial'),
                capacity=device.get('capacity'),
                state="In Progress",
                thread=grading_thread,
                progress_bar=progress_bar
            )

            # Resize Columns
            self.resize_jobs_columns()

            # Show Jobs Tab
            self.ui.tab_widget.setCurrentIndex(1)

        # Resize Columns
        self.resize_jobs_columns()

        # Show Jobs Tab
        self.ui.tab_widget.setCurrentIndex(1)

    @Slot()
    def process_selected_devices(self):
        """
        Process Selected Devices
        """

        # Execute Prompt, if not accepted, return
        if not GenericPromptDialog(self).exec() == QDialog.DialogCode.Accepted:
            # Return
            return

        # Get Selected Devices from Device Table
        devices = self.get_selected_devices_from_table()

        # Create Jobs
        for device in devices:
            # If DUT isn't in Control List
            if device['dut'] not in self.control_list:
                # Loop Jobs Table Rows
                for row in range(self.ui.jobs_table.rowCount() - 1, -1, -1):
                    # Get DUT
                    dut = self.ui.jobs_table.item(row, 0).text()

                    # If DUT match
                    if dut == device['dut']:
                        # Remove Row from Jobs Table
                        self.ui.jobs_table.removeRow(row)

            # Set Status
            device_status = QTableWidgetItem("Testing")
            device_status.setTextAlignment(align_center)
            device_status.setForeground(QBrush(QColor('red')))
            device_status.setIcon(QIcon(QPixmap(f'{app_path}/images/warning.png')))

            # Set Device Status
            self.ui.devices_table.setItem(device.get('row'), 2, device_status)

            # Set Row
            row = self.ui.jobs_table.rowCount()

            # Insert Row
            self.ui.jobs_table.insertRow(row)

            # Table Objects
            dut = QTableWidgetItem(device.get('dut'))
            model = QTableWidgetItem(device.get('model'))
            serial = QTableWidgetItem(device.get('serial'))
            capacity = QTableWidgetItem(device.get('capacity'))
            state = QTableWidgetItem("Starting")
            comments = QTableWidgetItem()

            # Grade Label
            grade = QLabel(grade_u)
            grade.setStyleSheet(pending_badge)
            grade.setAlignment(align_center)

            # Result Label
            result = QLabel("ONGOING")
            result.setStyleSheet(pending_badge)
            result.setAlignment(align_center)

            # Progress Bar
            progress_bar = QProgressBar()
            progress_bar.setValue(0)
            progress_bar.setRange(0, 100)
            progress_bar.setStyleSheet(pending_progress_bar)

            # Insert Cell Items
            self.ui.jobs_table.setItem(row, 0, dut)
            self.ui.jobs_table.setItem(row, 1, model)
            self.ui.jobs_table.setItem(row, 2, serial)
            self.ui.jobs_table.setItem(row, 3, capacity)
            self.ui.jobs_table.setItem(row, 4, state)
            self.ui.jobs_table.setCellWidget(row, 5, progress_bar)
            self.ui.jobs_table.setCellWidget(row, 6, result)
            self.ui.jobs_table.setCellWidget(row, 7, grade)
            self.ui.jobs_table.setItem(row, 8, comments)

            # Hide Grade Column
            self.ui.jobs_table.hideColumn(7)

            # Create Grading Thread
            grading_thread = Grading(device)
            grading_thread.finished.connect(self.finished)
            grading_thread.terminated.connect(self.terminated)
            grading_thread.raise_error_dialog.connect(self.raise_error_dialog)
            grading_thread.update_console.connect(self.update_console)
            grading_thread.update_control_list.connect(self.update_control_list)
            grading_thread.update_device_state.connect(self.update_device_state)
            grading_thread.update_progress.connect(progress_bar.setValue)
            grading_thread.update_message.connect(progress_bar.setFormat)
            grading_thread.update_progress_style.connect(progress_bar.setStyleSheet)
            grading_thread.update_state.connect(state.setText)
            grading_thread.update_result.connect(result.setText)
            grading_thread.update_result_style.connect(result.setStyleSheet)
            grading_thread.update_grade.connect(grade.setText)
            grading_thread.update_grade_style.connect(grade.setStyleSheet)
            grading_thread.update_comments.connect(comments.setText)
            grading_thread.start()

            # Add to Control List
            self.control_list[device.get('dut')] = dict(
                id=None,
                dut=device.get('dut'),
                model=device.get('model'),
                serial=device.get('serial'),
                capacity=device.get('capacity'),
                state="In Progress",
                thread=grading_thread,
                progress_bar=progress_bar
            )

            # Resize Columns
            self.resize_jobs_columns()

            # Show Jobs Tab
            self.ui.tab_widget.setCurrentIndex(1)

        # Resize Columns
        self.resize_jobs_columns()

        # Show Jobs Tab
        self.ui.tab_widget.setCurrentIndex(1)

    @Slot()
    def finished(self):
        """
        Finished Slot
        """

        # Try
        try:
            # Loop Control List Items
            for dut, data in self.control_list.copy().items():
                # If Sender is Thread
                if self.sender() == data['thread']:
                    # Remove from Control List
                    del self.control_list[dut]

        # Catch
        except Exception as exception:
            # Print
            print(exception)

    @Slot()
    def terminated(self):
        """
        Terminated Slot
        """

        # Try
        try:
            # Loop Control List Items
            for drive, data in self.control_list.copy().items():
                # If Sender is Thread
                if self.sender() == data['thread']:
                    # Stop Thread
                    self.control_list[drive]['thread'].stop()

        # Catch
        except Exception as exception:
            # Print
            print(exception)

    @Slot()
    def set_devices_table(self, devices):
        """
        Set Devices to Devices Table
        :param devices: devices iterable
        :return: bool
        """

        # Hide Headers
        self.ui.devices_table.horizontalHeader().hide()

        # Purge Devices Table
        self.purge_devices_table()

        # Purge Device Search Field
        self.purge_devices_search()

        # If there are no Devices
        if len(devices.devices) == 0:
            # Raise Exception
            raise NoDevicesDetectedException(message="No Devices detected during scan")

        # If there are any Failures
        if len(devices.failures) > 0:
            # pass
            pass

        # Set Devices Table Row Count
        self.ui.devices_table.setRowCount(len(devices.devices))

        # Set Device Count
        self.ui.devices_count.setText(f"Devices: " + str(len(devices.devices)))

        # Reset Counter
        i = 1

        # Enumerate Devices List
        for [row_id, device] in enumerate(devices.devices):
            # Create Device Information Items
            counter_item = QTableWidgetItem(str(i))  # Counter
            device_id_item = QTableWidgetItem(device.dut)  # Device ID/DUT
            device_state_item = QTableWidgetItem(device.state)  # Device Status
            device_vendor_item = QTableWidgetItem(device.vendor)  # Device Vendor/OEM
            device_model_item = QTableWidgetItem(device.model_number)  # Device Model Number
            device_serial_item = QTableWidgetItem(device.serial_number)  # Device Serial Number
            device_firmware_item = QTableWidgetItem(device.firmware_revision)  # Device Firmware Revision
            device_size_item = QTableWidgetItem(f"{str(device.gigabytes).split('.')[0]} GB")  # Device Size in GB
            device_block_item = QTableWidgetItem(str(device.logical_sector_size))  # Device Logical Sector Size
            device_poh_item = QTableWidgetItem(str(device.power_on_hours))  # Device Power On Hours

            # Create Progress Bar
            device_health_bar = QProgressBar()

            # Set Defaults
            health_value = 0
            progress_bar_style = failed_progress_bar

            # Device Health
            if device.health == "Not Reported":
                # Use Defaults
                pass

            # If Health
            elif device.health is not None and device.health != -1:
                # Set Health Value
                health_value = int(device.health)

                # If Health is 100 %
                if health_value == 100:
                    # Set Stylesheet
                    progress_bar_style = pass_progress_bar

                # If Health between 90 and 99 %
                elif 90 <= health_value <= 99:
                    # Set Stylesheet
                    progress_bar_style = pass_progress_bar

                # If Health between 50 and 89 %
                elif 50 <= health_value <= 89:
                    # Set Stylesheet
                    progress_bar_style = yellow_progress_bar

                # If Health between 1 and 49 %
                elif 1 <= health_value <= 49:
                    # Set Stylesheet
                    progress_bar_style = failed_progress_bar

            # Set Progress Bar and Stylesheet
            device_health_bar.setValue(health_value)
            device_health_bar.setStyleSheet(progress_bar_style)

            # Type Label
            device_media_type_item = QLabel(device.media_type)
            device_media_type_item.setAlignment(align_center)

            # If is SSD
            if device.is_ssd:
                # Set SSD
                device_media_type_item.setObjectName(device.media_type)
                device_media_type_item.setStyleSheet(ssd_badge)

            # If is HDD
            if device.is_hdd:
                # Set HDD
                device_media_type_item.setObjectName(device.media_type)
                device_media_type_item.setStyleSheet(hdd_badge)

            # Protocol Label
            device_transport_protocol_item = QLabel(device.transport_protocol)
            device_transport_protocol_item.setAlignment(align_center)

            # If is ATA
            if device.is_ata:
                # Set ATA Label
                device_transport_protocol_item.setText(device.transport_protocol)
                device_transport_protocol_item.setObjectName(device.transport_protocol)
                device_transport_protocol_item.setStyleSheet(ata_badge)

            # If is NVMe
            if device.is_nvme:
                # Set NVMe Label
                device_transport_protocol_item.setObjectName(device.transport_protocol)
                device_transport_protocol_item.setText(device.transport_protocol)
                device_transport_protocol_item.setStyleSheet(nvme_badge)

            # If is SCSI
            if device.is_scsi:
                # Set SCSI Label
                device_transport_protocol_item.setText(device.transport_protocol)
                device_transport_protocol_item.setObjectName(device.transport_protocol)
                device_transport_protocol_item.setStyleSheet(scsi_badge)

            # Temperature Label
            temperature_item = QLabel(device.temperature)
            temperature_item.setAlignment(align_center)

            # S.M.A.R.T Label
            device_smart_status_item = QLabel(f"OK" if device.smart_status else "FAIL")
            device_smart_status_item.setAlignment(align_center)
            device_smart_status_item.setStyleSheet(pass_badge if device.smart_status else failed_badge)

            # Grade Label
            device_grade_item = QLabel(device.cdi_grade)
            device_grade_item.setAlignment(align_center)

            # Grade Colour
            if device.cdi_grade == grade_a:
                # Set Grade to A Badge Style
                device_grade_item.setStyleSheet(pass_badge)
            elif device.cdi_grade == grade_b:
                # Set Grade to B Badge Style
                device_grade_item.setStyleSheet(pending_badge)
            elif device.cdi_grade == grade_c:
                # Set Grade to C Badge Style
                device_grade_item.setStyleSheet(pending_badge)
            elif device.cdi_grade == grade_d:
                # Set Grade to D Badge Style
                device_grade_item.setStyleSheet(pending_badge)
            elif device.cdi_grade == grade_e:
                # Set Grade to E Badge Style
                device_grade_item.setStyleSheet(pending_badge)
            elif device.cdi_grade == grade_f:
                # Set Grade to F Badge Style
                device_grade_item.setStyleSheet(failed_badge)
            elif device.cdi_grade == grade_u:
                # Set Grade to F Badge Style
                device_grade_item.setStyleSheet(pending_badge)

            # Custom Flags Widget
            device_flags = QWidget()

            # Create Flags Layout
            device_flags_layout = QHBoxLayout()

            # Set Flag Alignment
            device_flags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            # Set Margins
            device_flags_layout.setContentsMargins(5, 5, 5, 5)

            # Add Layout
            device_flags.setLayout(device_flags_layout)

            # Create Standard Flags
            regular_flags = defect_flags = warning_flags = []

            # Warning Flags
            warning_flags_list = [
                'Predicted to Fail',
                'Not ready',
                'Corrupt capacity',
                'Corrupt sector size',
                'Security frozen',
                'Security enabled',
                'Security locked',
                'HPA detected',
                'HPA I/O Error',
                'DCO detected',
                'AMAC detected',
                'TCG enabled',
                'Sanitize in progress',
            ]

            # Defect Flags
            defect_flags_list = [
                'Bad Sector',
                'Weak Sector',
                'Unstable Sector',
                'Reallocated Sector',
                'Uncorrectable Error',
                'Uncorrectable Read Error',
                'Uncorrectable Write Error',
                '% SSD Used',
                '% SSD Life Left',
                '% SSD Wear Level',
            ]

            # Loop Device Flags
            for flag in device.flags:
                # Create Flag Label
                label = QLabel(flag)

                # Set Flag Font
                label.setFont(QFont("Arial", 8))

                # If a Warning Flag
                if flag in warning_flags_list:
                    # Append to Warning Flags
                    warning_flags.append(label)

                    # Set Stylesheet
                    label.setStyleSheet(warning_badge)

                    # S.M.A.R.T Failure Tooltip
                    if "Predicted to Fail" in flag:
                        # Set Tooltip
                        label.setToolTip(predicted_to_fail_tooltip)

                # Iterate Defect Flags and check for Defect Flag
                if any(defect_flag in flag for defect_flag in defect_flags_list):
                    # Append to Warning Flags
                    defect_flags.append(label)

                    # Set Stylesheet
                    label.setStyleSheet(defect_badge)

                    # Reallocated Sectors Tooltip
                    if "Reallocated Sectors" in flag:
                        # Set Tooltip
                        label.setToolTip(reallocated_sectors_tooltip)

                    # Pending Sectors Tooltip
                    if "Unstable Sectors" in flag:
                        # Set Tooltip
                        label.setToolTip(pending_sectors_tooltip)

                    # Offline Uncorrectable Errors
                    if "Offline Uncorrectable Errors" in flag:
                        # Set Tooltip
                        label.setToolTip(uncorrectable_errors_tooltip)

                # Is a Regular Flag
                if flag not in warning_flags_list and not any(defect_flag in flag for defect_flag in defect_flags_list):
                    # Append to Regular Flags
                    regular_flags.append(label)

                    # Set Stylesheet
                    label.setStyleSheet(information_badge)

            # Loop Defect Flags
            for label in defect_flags:
                # Add Label
                device_flags_layout.addWidget(label)

            # Loop Regular Flags
            for label in regular_flags:
                # Add Label
                device_flags_layout.addWidget(label)

            # Loop Warning Flags
            for label in warning_flags:
                # Add Label
                device_flags_layout.addWidget(label)

            # Set Items
            self.ui.devices_table.setItem(row_id, 0, counter_item)
            self.ui.devices_table.setItem(row_id, 1, device_id_item)
            self.ui.devices_table.setItem(row_id, 2, device_state_item)
            self.ui.devices_table.setItem(row_id, 5, device_vendor_item)
            self.ui.devices_table.setItem(row_id, 6, device_model_item)
            self.ui.devices_table.setItem(row_id, 7, device_serial_item)
            self.ui.devices_table.setItem(row_id, 8, device_firmware_item)
            self.ui.devices_table.setItem(row_id, 9, device_size_item)
            self.ui.devices_table.setItem(row_id, 10, device_block_item)
            self.ui.devices_table.setItem(row_id, 11, device_poh_item)

            # Set Widgets
            self.ui.devices_table.setCellWidget(row_id, 3, device_media_type_item)
            self.ui.devices_table.setCellWidget(row_id, 4, device_transport_protocol_item)
            self.ui.devices_table.setCellWidget(row_id, 12, device_smart_status_item)
            self.ui.devices_table.setCellWidget(row_id, 13, device_grade_item)
            self.ui.devices_table.setCellWidget(row_id, 14, device_health_bar)
            self.ui.devices_table.setCellWidget(row_id, 15, device_flags)

            # Adjust Table Header Columns Size
            for column in range(self.ui.devices_table.columnCount()):
                # Set Resize Mode to Resize to Cell Contents
                self.ui.devices_table.horizontalHeader().setSectionResizeMode(column, resize_to_contents)

            # Loop Table Rows
            for row in range(self.ui.devices_table.rowCount()):
                # Loop Table Columns
                for column in range(self.ui.devices_table.columnCount() - 1):
                    # If Item
                    if self.ui.devices_table.item(row, column):
                        # Align Center
                        self.ui.devices_table.item(row, column).setTextAlignment(align_center)

            # Increment Counter
            i += 1

        # Show Headers
        self.ui.devices_table.horizontalHeader().show()

        # Hide Grade Column - TODO - Hidden for now - Implement a Grade
        self.ui.devices_table.hideColumn(13)

    @Slot()
    def refresh_devices_table(self):
        """
        Refresh Devices Table
        """

        # Purge Devices Table
        self.purge_devices_table()

        # Purge Device Search Field
        self.purge_devices_search()

        # Start Thread
        self.scanner.start()

    @Slot()
    def filter_devices_table(self):
        """
        Filter Devices Table
        """

        # Prepare Filter Dialog
        filter_dialog = FilterDialog(self)

        # If Filters
        if filter_dialog.exec():
            # Filter Devices Table
            for row_index in range(self.ui.devices_table.rowCount()):
                # Get Device Type
                device_type = self.ui.devices_table.cellWidget(row_index, 3).text().lower()

                # Get Device Protocol
                device_protocol = self.ui.devices_table.cellWidget(row_index, 4).text().lower()

                # Check Filters and Information
                if (filter_dialog.filters["HDD"] and "hdd" in device_type) or (filter_dialog.filters["SSD"] and "ssd" in device_type) or (filter_dialog.filters["ATA"] and "ata" in device_protocol) or (filter_dialog.filters["NVMe"] and "nvme" in device_protocol) or (filter_dialog.filters["SCSI"] and "scsi" in device_protocol):
                    # Show Row
                    self.ui.devices_table.setRowHidden(row_index, False)

                # Else
                else:
                    # Hide Row
                    self.ui.devices_table.setRowHidden(row_index, True)

    @Slot()
    def search_devices_table(self):
        """
        Search Devices Table
        :return:
        """

        # Reset Counter
        visible_counter = 0

        # Get Search Text
        devices_search_text = self.ui.devices_search_field.text().lower()

        # Loop Table Rows
        for row in range(self.ui.devices_table.rowCount()):
            # Reset Contains Flag
            label_contains_text = False

            # Loop Table Columns
            for column in range(self.ui.devices_table.columnCount()):
                # Get Item
                item = self.ui.devices_table.item(row, column)

                # Get Cell Widget
                cell_widget = self.ui.devices_table.cellWidget(row, column)

                # If is a QTableWidgetItem
                if item is not None:
                    # Get Cell Text
                    cell_text = item.text().lower()

                    # Check Search Text
                    if devices_search_text in cell_text:
                        # Set Contains Flag True
                        label_contains_text = True

                        # Break
                        break

                # If is a QLabel
                elif cell_widget is not None and isinstance(cell_widget, QLabel):
                    # Get Cell Widget Text
                    cell_widget_text = cell_widget.text().lower()

                    # Check Search Text
                    if devices_search_text in cell_widget_text:
                        # Set Contains Flag True
                        label_contains_text = True

                        # Break
                        break

                # If is a QWidget
                elif cell_widget is not None and isinstance(cell_widget, QWidget):
                    # If is a QProgressBar, skip for now
                    if isinstance(cell_widget, QProgressBar):
                        continue

                    # Get Layout
                    layout = cell_widget.layout()

                    # Loop Layout Items
                    for i in range(layout.count()):
                        # Get Widget
                        widget = layout.itemAt(i).widget()

                        # If QLabel
                        if isinstance(widget, QLabel):
                            # Get QLabel Text
                            label_text = widget.text().lower()

                            # Check Search Text
                            if devices_search_text in label_text:
                                # Set Contains Flag True
                                label_contains_text = True

                                # Break
                                break

                    # If Label Contains Text
                    if label_contains_text:
                        # Break
                        break

            # If Contains Text
            if label_contains_text:
                # Show Row
                self.ui.devices_table.setRowHidden(row, False)

                # Increment Counter
                visible_counter += 1

            # Else
            else:
                # Hide Row
                self.ui.devices_table.setRowHidden(row, True)

        # Update Counter
        self.ui.devices_count.setText(f"Devices: {visible_counter}")

    @Slot()
    def purge_devices_search(self):
        """
        Purge Device Search
        :return:
        """

        # Clear
        self.ui.devices_search_field.clear()

    @Slot()
    def purge_devices_table(self):
        """
        Purge Devices Table
        :return: bool
        """

        # Clear
        self.ui.devices_table.clearContents()

        # Reset
        self.ui.devices_table.setRowCount(0)

        # Disable
        # self.ui.devices_table.setSortingEnabled(False)

        # Enable
        # self.ui.devices_table.setSortingEnabled(True)

        # Sort
        # self.ui.devices_table.sortItems(0)

    """
    Jobs
    """

    @Slot()
    def resize_jobs_columns(self):
        """
        Resize Job Columns
        """

        # Get Header
        horizontal_header = self.ui.jobs_table.horizontalHeader()

        # Set Fixed
        horizontal_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        # Set Column Widths
        horizontal_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)

        # Set Progress Bar Column Width
        self.ui.jobs_table.setColumnWidth(5, 380)

        # Loop Rows
        for row in range(self.ui.jobs_table.rowCount()):
            # Loop Columns
            for column in range(self.ui.jobs_table.columnCount() - 1):
                # Get Item
                item = self.ui.jobs_table.item(row, column)

                # If Item
                if item:
                    # Align Center
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    @Slot()
    def search_jobs_table(self):
        """
        Search Jobs Table
        :return:
        """

        # Get Search Text
        jobs_search_text = self.ui.jobs_search_field.text().lower()

        # Counter
        visible_counter = 0

        # Loop Table Rows
        for row in range(self.ui.jobs_table.rowCount()):
            # Loop Columns
            for column in range(self.ui.jobs_table.columnCount()):
                # Get Item
                item = self.ui.jobs_table.item(row, column)

                # Get Cell Widget
                cell_widget = self.ui.jobs_table.cellWidget(row, column)

                # Check contains Text
                if item is not None:
                    # Get Cell Text
                    cell_text = item.text().lower()

                    # Check Search Text
                    if jobs_search_text in cell_text:
                        # Show Row
                        self.ui.jobs_table.setRowHidden(row, False)

                        # Increment Counter
                        visible_counter += 1

                        # Break
                        break
                    else:
                        # Hide Row
                        self.ui.jobs_table.setRowHidden(row, True)

                # If contains Widget and widget is QLabel
                elif cell_widget is not None and isinstance(cell_widget, QLabel):
                    # Get Cell Widget Text
                    cell_widget_text = cell_widget.text().lower()

                    # Check Search Text
                    if jobs_search_text in cell_widget_text:
                        # Show Row
                        self.ui.jobs_table.setRowHidden(row, False)

                        # Increment Counter
                        visible_counter += 1

                        # Break
                        break
                    else:
                        # Hide Row
                        self.ui.jobs_table.setRowHidden(row, True)

        # Update Device Counter
        self.ui.jobs_count.setText(f"Jobs: {visible_counter}")

    """
    Tools
    """

    @Slot()
    def show_hdparm_as_text(self):
        """
        Show HDParm Output as Text
        :return: QDialog
        """

        # Get Device
        device = self.get_selected_device_from_table()

        # HDSentinel
        hdsentinel = GenericCommandDialog(
            parent=self,
            device=device['dut'],
            title=f"HDParm - Get All - Text - {device['dut']} - {device['model']}",
            command=f"hdparm -I {device['dut']}",
        )

        # Execute HDSentinel
        return hdsentinel.exec()

    @Slot()
    def show_hdsentinel_as_text(self):
        """
        Show HDSentinel Output as Text
        :return: QDialog
        """

        # Get Device
        device = self.get_selected_device_from_table()

        # HDSentinel
        hdsentinel = GenericCommandDialog(
            parent=self,
            device=device['dut'],
            title=f"HDSentinel - Get All - Text - {device['dut']} - {device['model']}",
            command=f"hdsentinel -dump -dev {device['dut']}",
            include_html_output=True,
            include_json_output=True,
            include_xml_output=True
        )

        # Execute HDSentinel
        return hdsentinel.exec()

    @Slot()
    def show_smartctl_as_text(self):
        """
        Show Smartctl Output as Text
        :return: QDialog
        """

        # Get Device
        device = self.get_selected_device_from_table()

        # Smartctl
        smartctl = GenericCommandDialog(
            parent=self,
            device=device['dut'],
            title=f"Smartctl - Get All - Text - {device['dut']} - {device['model']}",
            command=f"smartctl -x {device['dut']}",
            include_json_output=True
        )

        # Execute Smartctl
        return smartctl.exec()

    @Slot()
    def show_seatools_as_text(self):
        """
        Show SeaTools Output as Text
        :return: QDialog
        """

        # Get Device
        device = self.get_selected_device_from_table()

        # SeaTools
        seatools = GenericCommandDialog(
            parent=self,
            device="/dev/sdb",
            title=f"SeaTools - Get All - Text - {device['dut']} - {device['model']}",
            command=f"/opt/openSeaChest/openSeaChest_Basics --noBanner -i -d {device['dut']}"
        )

        # Execute SeaTools
        return seatools.exec()

    @Slot()
    def show_sedutil_as_text(self):
        # Get Device
        device = self.get_selected_device_from_table()

        # Sedutil
        sedutil = GenericCommandDialog(
            parent=self,
            device="/dev/sdb",
            title=f"Sedutil - Get All - Text - {device['dut']} - {device['model']}",
            command=f"sedutil-cli --query {device['dut']}"
        )

        # Execute Sedutil
        return sedutil.exec()

