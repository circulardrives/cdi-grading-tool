"""
Circular Drive Initiative - Widget Classes

@language    Python 3.12
@framework   PySide 6
@version     0.0.1
"""

# Modules
import math
import subprocess
import sys

# PySide6
from PySide6.QtCore import Qt, QSize, QTimer, QRect
from PySide6.QtGui import QFont, QIcon, QColor, QPaintEvent, QPainter
from PySide6.QtWidgets import QDialog, QFormLayout, QPushButton, QVBoxLayout, QLabel, QHBoxLayout, QTextBrowser, QGroupBox, QCommandLinkButton, QFileDialog, QMessageBox, QWidget, QCheckBox

from classes.tools import Command
from constants import dialog_stylesheet, eula, images_path, reboot_now, sleep_now, shutdown_now


class FilterDialog(QDialog):
    """
    Filter Dialog
    """

    def __init__(self, parent=None):
        """
        Constructor
        :param parent:
        """

        # Initialize Parent
        super().__init__(parent)

        # Filters
        self.filters = None

        # Set Window Title
        self.setWindowTitle("Filter")

        # Set font for labels and checkboxes
        font = QFont()
        font.setPointSize(12)

        # Media Types
        self.hdd_checkbox = QCheckBox("HDD")
        self.hdd_checkbox.setFont(font)
        self.ssd_checkbox = QCheckBox("SSD")
        self.ssd_checkbox.setFont(font)

        # Transport Protocols
        self.ata_checkbox = QCheckBox("ATA")
        self.ata_checkbox.setFont(font)
        self.nvme_checkbox = QCheckBox("NVMe")
        self.nvme_checkbox.setFont(font)
        self.scsi_checkbox = QCheckBox("SCSI")
        self.scsi_checkbox.setFont(font)

        # Create Form Layout
        form_layout = QFormLayout()

        # Media Type
        form_layout.addRow("<strong>Media Type:</strong>", self.hdd_checkbox)
        form_layout.addRow("", self.ssd_checkbox)

        # Transport Protocol
        form_layout.addRow("Transport Protocol:", self.ata_checkbox)
        form_layout.addRow("", self.nvme_checkbox)
        form_layout.addRow("", self.scsi_checkbox)

        # Create Apply Filters
        self.apply_button = QPushButton("Apply Filters")
        self.apply_button.setFont(font)

        # Connect Signal
        self.apply_button.clicked.connect(self.apply_filters)

        # Create Layout
        layout = QVBoxLayout()

        # Add Layout
        layout.addLayout(form_layout)

        # Add Widget
        layout.addWidget(self.apply_button)

        # Set Layout
        self.setLayout(layout)

        # Apply Bootstrap-style theme
        self.setStyleSheet("""
            QDialog {
                background-color: #343a40;
            }
            QLabel {
                color: #f8f9fa;
                font-size: 12px;
            }
            QCheckBox {
                color: #f8f9fa;
                font-size: 12px;
            }
            QPushButton {
                background-color: #007bff;
                color: #ffffff;
                font-size: 12px;
                border: 1px solid #007bff;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #0056b3;
            }
        """)

    def apply_filters(self):
        """
        Apply Filters
        :return: Dictionary containing selected filters
        """

        # Get Filters
        filters = {
            "HDD": self.hdd_checkbox.isChecked(),
            "SSD": self.ssd_checkbox.isChecked(),
            "ATA": self.ata_checkbox.isChecked(),
            "NVMe": self.nvme_checkbox.isChecked(),
            "SCSI": self.scsi_checkbox.isChecked()
        }

        # Loop Filters
        for filter_name, is_checked in filters.items():
            # If Checked
            if is_checked:
                # Print
                print(filter_name)

        # Filters
        self.filters = filters

        # Accept
        self.accept()


class GenericDialog(QDialog):
    """
    Generic Prompt
    """

    def __init__(self, parent, title, description):
        """
        Constructor
        :param parent: parent widget (usually QMainWindow)
        :param title: title string for the QDialog Window
        :param description: description string for the QDialog Window
        """

        # Initialize Parent
        super().__init__(parent)

        # Set Window Title
        self.setWindowTitle(title)

        # Create Description Label
        self.description_label = QLabel(description)

        # Create Buttons
        self.ok_button = QPushButton("OK", objectName="confirm-button")
        self.cancel_button = QPushButton("Cancel", objectName="cancel-button")

        # Create Main Layout
        self.layout = QVBoxLayout()

        # Add Description Label
        self.layout.addWidget(self.description_label)

        # Create Button Layout
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.cancel_button)
        self.buttons_layout.addWidget(self.ok_button)

        # Add Button Layout
        self.layout.addLayout(self.buttons_layout)

        # Set Layout
        self.setLayout(self.layout)

        # Connect Buttons
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Set Stylesheet
        self.setStyleSheet(dialog_stylesheet)

        # Show
        self.show()


class GenericCommandDialog(QDialog):
    """
    Generic Command Dialog
    """

    def __init__(self, parent, title, command, device, include_html_output=False, include_json_output=False, include_xml_output=False):
        # Initialize
        super().__init__(parent)

        # Device
        self.title = title
        self.device = device
        self.command = command

        # Window Title
        self.setWindowTitle(f"{self.title}")

        # Prepare Command
        command = Command(command=self.command)

        # Run Command
        command.run()

        # Create widgets
        self.text_browser = QTextBrowser()

        # Create layout
        generic_command_output_layout = QVBoxLayout()

        # Create GroupBox
        generic_command_group_box = QGroupBox("Export Options")

        # Create Button Layout
        generic_command_output_button_layout = QHBoxLayout()

        # Create Export Text Report Button
        generic_command_output_export_button = QCommandLinkButton("Save Text Report", "Generate a Text Report")

        # Add Buttons
        generic_command_output_button_layout.addWidget(generic_command_output_export_button)

        # Connect Button Signals to Slots
        generic_command_output_export_button.clicked.connect(self.export_output)

        # If Include HTML Output
        if include_html_output:
            # Create Export HTML Report Button
            generic_command_output_export_html_button = QCommandLinkButton(
                "Save HTML Report",
                "Generate an HTML report"
            )

            # Connect Button Signals to Slots
            generic_command_output_export_html_button.clicked.connect(self.export_html)

            # Add HTML Button
            generic_command_output_button_layout.addWidget(generic_command_output_export_html_button)

        # If Include JSON Output
        if include_json_output:
            # Create Export JSON Report Button
            generic_command_output_export_json_button = QCommandLinkButton(
                "Save JSON Report",
                "Generate a JSON report"
            )

            # Connect Button Signals to Slots
            generic_command_output_export_json_button.clicked.connect(self.export_json)

            # Add JSON Button
            generic_command_output_button_layout.addWidget(generic_command_output_export_json_button)

        # If Include XML Output
        if include_xml_output:
            # Create Export XML Report Button
            generic_command_output_export_xml_button = QCommandLinkButton(
                "Save XML Report",
                "Generate an XML report"
            )

            # Connect Button Signals to Slots
            generic_command_output_export_xml_button.clicked.connect(self.export_html)

            # Add HTML Button
            generic_command_output_button_layout.addWidget(generic_command_output_export_xml_button)

        # Add Button Layout to GroupBox
        generic_command_group_box.setLayout(generic_command_output_button_layout)

        # Add GroupBox to Layout
        generic_command_output_layout.addWidget(generic_command_group_box)

        # Add Text Browser to Layout
        generic_command_output_layout.addWidget(self.text_browser)

        # Set Layout
        self.setLayout(generic_command_output_layout)

        # Set Text Browser Text
        self.text_browser.setPlainText(command.get_output().decode('latin'))

        # Set Stylesheet
        self.text_browser.setStyleSheet(
            """
            background: white;
            font: Liberation Mono;
            font-size: 12px;
            color: black;
            """
        )

        # Resize
        self.showMaximized()

    def export_output(self):
        """
        Export/Save Text Output
        """

        # Get File Dialog Options
        options = QFileDialog.Option(self)

        # Set Filename
        default_filename = f"{self.device['model']}_{self.device['serial']}_smartctl.txt"

        # Open Dialog and Capture File Name
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export Text Report",
            f"/home/reports/{default_filename}",
            "Text Files (*.txt)",
            options=options
        )

        # If File Name
        if not file_name:
            # Return
            return

        # Open File
        with open(file_name, "w") as f:
            # Write File
            f.write(self.text_browser.toPlainText())

    def export_html(self):
        """
        Export/Save HDSentinel HTML Report
        """

        # Get File Dialog Options
        options = QFileDialog.Option(self)

        # Open Dialog and Capture File Name
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export HTML Report",
            "/home/reports",
            "HTML Files (*.html)",
            options=options
        )

        # Command
        cmd = f"hdsentinel -dump -dev {self.device['dut']} -html -r {file_name}"

        # Execute Scan
        subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    def export_json(self):
        pass


class GenericPromptDialog(QDialog):
    """
    Process Selected Prompt
    """

    def __init__(self, parent):
        # Initialize
        super().__init__(parent)

        # Set Window Title
        self.setWindowTitle("CDI Grading Tool | EULA")

        # Information Label
        self.info_label = QLabel(
            f'''
            <p>By clicking Yes, you are agreeing to the terms of the CDI Grading Tool End User License Agreement (EULA).</p>
            <p>You are about to process <b>ALL SELECTED</b> drives in the table which could include S.M.A.R.T Testing and Read/Write Testing.</p>
            <p><b>Please review the following notes before proceeding:</b></p>
            <ol class="modal-list">
                <li><b style="color:red;">WARNING - THIS GRADING TOOL CAN WRITE DATA TO THE DISK. PLEASE ENSURE DATA IS BACKED UP!</b></li>
                <li>Where possible, avoid mixing transport protocols. Try to process batches of devices that use the same protocol.</li>
            </ol>
            <p class="modal-note">NOTE: This action is <b>irreversible</b>. Please click Yes to confirm grading, or click No to go back and cancel.</p>
            '''
        )

        # Create Layout
        layout = QVBoxLayout()

        # Add Info Label
        layout.addWidget(self.info_label)

        # Buttons
        self.ok_button = QPushButton("Yes, Confirm and Grade", objectName="confirm-button")
        self.cancel_button = QPushButton("No, Cancel and Go Back", objectName="cancel-button")
        self.view_eula_button = QPushButton("View EULA", objectName="view-eula-button")

        # Create Button Layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.view_eula_button)
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.ok_button)

        # Add Button Layout
        layout.addLayout(buttons_layout)

        # Set Spacing
        layout.setSpacing(15)

        # Set Layout
        self.setLayout(layout)

        # Connect Buttons to slots
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.view_eula_button.clicked.connect(self.show_eula_dialog)

        # Add Bootstrap Style
        self.setStyleSheet(
            """
            QDialog {
                background-color: #fff;
                color: #212529;
                color: #000;
            }

            QPushButton {
                font-size: 14px;
                font-weight: bold;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
            }

            QLabel {
                font-size: 14px;
                color: black;
            }

            h2.modal-title {
                font-size: 24px;
                color: #dc3545;
                margin-bottom: 20px;
            }

            ol.modal-list {
                font-size: 14px;
            }

            p.modal-note {
                font-size: 12px;
                font-style: italic;
                color: gray;
                margin-top: 20px;
            }

            ol.modal-list li {
                margin-bottom: 10px;
            }

            QPushButton#confirm-button {
                background-color: #dc3545;
                color: #fff;
            }

            QPushButton#cancel-button {
                background-color: #6c757d;
                color: #fff;
            }

            QPushButton#view-eula-button {
                background-color: #6c757d;
                color: #fff;
            }
            """
        )

    def show_eula_dialog(self):
        """
        Show End User License Agreement
        :return:
        """

        # Create Dialog
        eula_dialog = QDialog(self)

        # Set Window Title
        eula_dialog.setWindowTitle("CDI Grading Tool | End User License Agreement")

        # Create Layout
        layout = QVBoxLayout()

        # Create Text Browser
        eula_browser = QTextBrowser()

        # Hide Scrollbar
        eula_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Read EULA
        with open(eula, "r") as file:
            # Get Text
            eula_text = file.read()

        # Set EULA Text
        eula_browser.setHtml(eula_text)

        # Set Stylesheet
        eula_browser.setStyleSheet('background-color:white;color:black;')

        # Add Widget to Layout
        layout.addWidget(eula_browser)

        # Set Layout to EULA Dialog
        eula_dialog.setLayout(layout)

        # Resize Dialog
        eula_dialog.resize(1024, 768)

        # Show Dialog
        eula_dialog.exec()


class PowerDialog(QMessageBox):
    """
    Power Dialog
    """

    def __init__(self, parent, title, text):
        """
        Constructor
        @param parent: parent widget
        @param title: the title of the widget
        @param text: the text of the widget
        """

        # Initialize
        super().__init__(parent)

        # Set Window Title
        self.setWindowTitle(f"{title}")

        # Set Icon
        self.setIconPixmap(QIcon(f"{images_path}/icon.png").pixmap(QSize(42, 42)))

        # Set Text
        self.setText(text)

        # Set Frameless
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        # Create buttons

        self.exit_button = QPushButton("Exit")
        self.sleep_button = QPushButton("Sleep")
        self.cancel_button = QPushButton("Cancel")
        self.restart_button = QPushButton("Restart")
        self.shutdown_button = QPushButton("Shutdown")

        # Button Style
        button_style = """
            QPushButton {
                background-color: #5b636a;
                color: #fff;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3b754a;
            }
            QPushButton:pressed {
                background-color: #3b754a;
            }
        """

        # Set Stylesheet to Buttons
        self.cancel_button.setStyleSheet(button_style)
        self.exit_button.setStyleSheet(button_style)
        self.restart_button.setStyleSheet(button_style)
        self.sleep_button.setStyleSheet(button_style)
        self.shutdown_button.setStyleSheet(button_style)

        # Add Buttons to Message Box
        self.addButton(self.cancel_button, QMessageBox.ButtonRole.RejectRole)
        self.addButton(self.exit_button, QMessageBox.ButtonRole.ActionRole)
        self.addButton(self.restart_button, QMessageBox.ButtonRole.ActionRole)
        self.addButton(self.sleep_button, QMessageBox.ButtonRole.ActionRole)
        self.addButton(self.shutdown_button, QMessageBox.ButtonRole.ActionRole)

        # Connect Buttons to Slots
        self.cancel_button.clicked.connect(self.reject)
        self.exit_button.clicked.connect(self.exit_slot)
        self.sleep_button.clicked.connect(self.sleep_slot)
        self.restart_button.clicked.connect(self.restart_slot)
        self.shutdown_button.clicked.connect(self.shutdown_slot)

    @staticmethod
    def exit_slot():
        """
        Slot for Exit button
        """

        # Exit
        sys.exit("Closed by Exit Button")

    @staticmethod
    def restart_slot():
        """
        Slot for Restart button
        """

        # Execute Reboot
        return subprocess.run(reboot_now)

    @staticmethod
    def sleep_slot():
        """
        Slot for Sleep button
        """

        # Execute Sleep Slot
        return subprocess.run(sleep_now)

    @staticmethod
    def shutdown_slot():
        """
        Slot for Shutdown button
        """

        # Execute Shutdown
        return subprocess.run(shutdown_now)


class Spinner(QWidget):
    """
    Spinner Class
    """

    def __init__(self, parent: QWidget, center_on_parent: bool = True, disable_parent_when_spinning: bool = False, modality: Qt.WindowModality = Qt.NonModal, roundness: float = 100.0, fade: float = 80.0, lines: int = 15, line_length: int = 10, line_width: int = 2, radius: int = 10, speed: float = math.pi / 2, color: QColor = QColor(0, 0, 0)) -> None:
        """
        Constructor
        :param parent:
        :param center_on_parent:
        :param disable_parent_when_spinning:
        :param modality:
        :param roundness:
        :param fade:
        :param lines:
        :param line_length:
        :param line_width:
        :param radius:
        :param speed:
        :param color:
        """

        # Initialize Parent
        super().__init__(parent)

        # Center Parent Widget
        self._center_on_parent: bool = center_on_parent

        # Disable Parent Widget
        self._disable_parent_when_spinning: bool = disable_parent_when_spinning

        # Properties
        self._color: QColor = color
        self._roundness: float = roundness
        self._minimum_trail_opacity: float = math.pi
        self._trail_fade_percentage: float = fade
        self._revolutions_per_second: float = speed
        self._number_of_lines: int = lines
        self._line_length: int = line_length
        self._line_width: int = line_width
        self._inner_radius: int = radius
        self._current_counter: int = 0
        self._is_spinning: bool = False

        # Timer
        self._timer: QTimer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._update_size()
        self._update_timer()

        # Set Window Modality
        self.setWindowModality(modality)

        # Set Translucent Background
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Hide
        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint
        """

        # Update Current Position
        self._update_position()

        # Create Painter
        painter = QPainter(self)

        # Fill Rectangle
        painter.fillRect(self.rect(), Qt.transparent)

        # Set Render Hint
        painter.setRenderHint(QPainter.Antialiasing, True)

        # If Counter is greater than number of Lines
        if self._current_counter >= self._number_of_lines:
            # Reset Counter
            self._current_counter = 0

        # Set Pen
        painter.setPen(Qt.NoPen)

        # Loop Lines
        for i in range(self._number_of_lines):
            # Save
            painter.save()

            # Translate
            painter.translate(self._inner_radius + self._line_length, self._inner_radius + self._line_length)

            # Set Rotation Angle
            rotate_angle = 360 * i / self._number_of_lines

            # Rotate
            painter.rotate(rotate_angle)

            # Translate
            painter.translate(self._inner_radius, 0)

            # Calculate Distance
            distance = self._line_count_distance_from_primary(i, self._current_counter, self._number_of_lines)

            # Set Color
            color = self._current_line_color(
                distance,
                self._number_of_lines,
                self._trail_fade_percentage,
                self._minimum_trail_opacity,
                self._color,
            )

            # Set Brush Color
            painter.setBrush(color)

            # Draw Rounded Rectangle
            painter.drawRoundedRect(
                QRect(
                    0,
                    -self._line_width // 2,
                    self._line_length,
                    self._line_width,
                ),
                self._roundness,
                self._roundness,
                Qt.RelativeSize,
            )

            # Restore
            painter.restore()

    def start(self) -> None:
        """
        Start the QWaitingSpinner
        :return:
        """

        # Update Position
        self._update_position()

        # Set is Spinning
        self._is_spinning = True

        # Show Spinner
        self.show()

        # If Parent Widget and Disable Parent Widget
        if self.parentWidget and self._disable_parent_when_spinning:
            # Disable Parent Widget
            self.parentWidget().setEnabled(False)

        # If Timer is not Active
        if not self._timer.isActive():
            # Start Timer
            self._timer.start()

            # Reset Counter
            self._current_counter = 0

    def stop(self) -> None:
        """
        Stop the QWaitingSpinner
        :return:
        """

        self._is_spinning = False
        self.hide()

        if self.parentWidget() and self._disable_parent_when_spinning:
            self.parentWidget().setEnabled(True)

        if self._timer.isActive():
            self._timer.stop()
            self._current_counter = 0

    @property
    def color(self) -> QColor:
        """
        Get Color
        """

        # Return Color
        return self._color

    @color.setter
    def color(self, color: Qt.GlobalColor = Qt.black) -> None:
        """
        Set Color
        """

        # Set Color
        self._color = QColor(color)

    @property
    def roundness(self) -> float:
        """
        Get Roundness
        :return: float
        """

        # Return Roundness
        return self._roundness

    @roundness.setter
    def roundness(self, roundness: float) -> None:
        """
        Set Roundness
        """

        # Set Roundness
        self._roundness = max(0.0, min(100.0, roundness))

    @property
    def minimum_trail_opacity(self) -> float:
        """
        Get Trail Opacity
        """

        # Return Trail Opacity
        return self._minimum_trail_opacity

    @minimum_trail_opacity.setter
    def minimum_trail_opacity(self, minimum_trail_opacity: float) -> None:
        """
        Set Trail Opacity
        """

        # Set Minimum Trail Opacity
        self._minimum_trail_opacity = minimum_trail_opacity

    @property
    def trail_fade_percentage(self) -> float:
        """
        Get Trail Fade Percentage
        """

        # Return Fade Percentage
        return self._trail_fade_percentage

    @trail_fade_percentage.setter
    def trail_fade_percentage(self, trail: float) -> None:
        """
        Set Trail Fade Percentage
        """

        # Set Trail Fade Percentage
        self._trail_fade_percentage = trail

    @property
    def revolutions_per_second(self) -> float:
        """
        Get Revolutions per Second
        """

        # Return RPS
        return self._revolutions_per_second

    @revolutions_per_second.setter
    def revolutions_per_second(self, revolutions_per_second: float) -> None:
        """
        Set Revolutions per Second
        """

        # Set RPS
        self._revolutions_per_second = revolutions_per_second

        # Update Timer
        self._update_timer()

    @property
    def number_of_lines(self) -> int:
        """
        Get Number of Lines
        :return: int: Number of Lines
        """

        # Return Number of Lines
        return self._number_of_lines

    @number_of_lines.setter
    def number_of_lines(self, lines: int) -> None:
        """
        Set Number of Lines
        :param lines: Number of Lines
        :return:
        """

        # Set Number of Lines
        self._number_of_lines = lines

        # Reset Counter
        self._current_counter = 0

        # Update Timer
        self._update_timer()

    @property
    def line_length(self) -> int:
        """
        Get Line Length
        :return:
        """

        # Return Line Length
        return self._line_length

    @line_length.setter
    def line_length(self, length: int) -> None:
        """
        Set Line Length
        :return:
        """

        # Set Line Length
        self._line_length = length

        # Update Size
        self._update_size()

    @property
    def line_width(self) -> int:
        """
        Get Line Width
        :return:
        """

        # Return Line Width
        return self._line_width

    @line_width.setter
    def line_width(self, width: int) -> None:
        """
        Set Line Width
        :return:
        """

        # Set Line Width
        self._line_width = width

        # Update Size
        self._update_size()

    @property
    def inner_radius(self) -> int:
        """
        Get Inner Radius
        :return:
        """

        # Return Inner Radius
        return self._inner_radius

    @inner_radius.setter
    def inner_radius(self, radius: int) -> None:
        """
        Set Inner Radius
        :return:
        """

        # Set Inner Radius
        self._inner_radius = radius

        # Update Size
        self._update_size()

    @property
    def is_spinning(self) -> bool:
        """
        Is Spinning?
        :return: bool: Is spinning
        """

        # Return Is Spinning
        return self._is_spinning

    def _rotate(self) -> None:
        """
        Rotate
        :return:
        """

        # Set Counter
        self._current_counter += 1

        # If greater than number of lines
        if self._current_counter >= self._number_of_lines:
            # Reset Counter
            self._current_counter = 0

        # Update Widget
        self.update()

    def _update_size(self) -> None:
        """
        Update Size
        :return:
        """

        # Get Size
        size = (self._inner_radius + self._line_length) * 2

        # Set Size
        self.setFixedSize(size, size)

    def _update_timer(self) -> None:
        """
        Update Timer
        :return:
        """

        # Set Timer Interval
        self._timer.setInterval(int(1000 / (self._number_of_lines * self._revolutions_per_second)))

    def _update_position(self) -> None:
        """
        Update Position
        :return:
        """

        # If Parent Widget and Center on Parent
        if self.parentWidget() and self._center_on_parent:
            self.move((self.parentWidget().width() - self.width()) // 2, (self.parentWidget().height() - self.height()) // 2)

    @staticmethod
    def _line_count_distance_from_primary(current: int, primary: int, total_nr_of_lines: int) -> int:
        """
        Return the Distance from Counter
        :param current:
        :param primary:
        :param total_nr_of_lines:
        :return:
        """

        # Distance
        distance = primary - current

        # If Zero
        if distance < 0:
            # Increment by Number of Lines
            distance += total_nr_of_lines

        # Return Distance
        return distance

    @staticmethod
    def _current_line_color(count_distance: int, total_nr_of_lines: int, trail_fade_perc: float, min_opacity: float, color_input: QColor) -> QColor:
        """
        Get Current Line Color
        :param count_distance:
        :param total_nr_of_lines:
        :param trail_fade_perc:
        :param min_opacity:
        :param color_input:
        :return:
        """

        # Set Color
        color = QColor(color_input)

        # If Distance is Zero
        if count_distance == 0:
            # Return Color
            return color

        # Get Minimum Alpha
        min_alpha_f = min_opacity / 100.0

        # Set Threshold
        distance_threshold = int(math.ceil((total_nr_of_lines - 1) * trail_fade_perc / 100.0))

        # If Distance exceeds Threshold
        if count_distance > distance_threshold:
            # Set Minimum Alpha
            color.setAlphaF(min_alpha_f)
        else:
            # Set Alpha
            alpha_diff = color.alphaF() - min_alpha_f

            # Set Gradient
            gradient = alpha_diff / float(distance_threshold + 1)

            # Set Result Alpha
            result_alpha = color.alphaF() - gradient * count_distance

            # Clip Alpha if required
            result_alpha = min(1.0, max(0.0, result_alpha))

            # Set Alpha
            color.setAlphaF(result_alpha)

        # Return Color
        return color