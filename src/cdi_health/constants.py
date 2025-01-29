#
# Copyright (c) 2024 Circular Drive Initiative.
#
# This file is part of CDI Health.
# See https://github.com/circulardrives/cdi-grading-tool-alpha/ for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Circular Drive Initiative - Constants

@language    Python 3.12
@framework   PySide 6
@version     0.0.1
"""

# TODO: manage via isort
from __future__ import annotations

# Modules
import os
import sys

"""
APP
"""

# Set OS Runtime Environment
os.environ["XDG_RUNTIME_DIR"] = "/run/cdi_grading"

# Application Paths
application_directory = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
app_path = os.path.abspath(os.path.join(application_directory))
config_path = os.path.join(app_path, "config")
images_path = os.path.join(app_path, "images")
reports_path = os.path.join(app_path, "reports")
logs_path = os.path.join(app_path, "logs")

# EULA File
eula = f"{config_path}/eula.html"

# Configuration File
configuration_file = f"{config_path}/configuration.ini"

# Splashscreen Properties
splashscreen = f"{images_path}/cdi.jpg"
splashscreen_height = 1440
splashscreen_width = 1440

"""
Stylesheets
"""

# Stylesheet Properties
dialog_stylesheet = """
    QDialog {
        background-color: #f8f9fa;
        color: #212529;
    }

    QPushButton {
        font-size: 14px;
        font-weight: bold;
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        background-color: #007bff;
        color: #fff;
    }

    QPushButton:hover {
        background-color: #0056b3;
    }

    QLabel {
        font-size: 14px;
        color: #000;
    }

    h2.modal-title {
        font-size: 24px;
        color: #007bff;
        margin-bottom: 20px;
    }

    ol.modal-list {
        font-size: 14px;
    }

    p.modal-note {
        font-size: 12px;
        font-style: italic;
        color: #6c757d;
        margin-top: 20px;
    }

    ol.modal-list li {
        margin-bottom: 10px;
    }
    """

# ATA/SATA Badge Stylesheet
ata_badge = """ 
    QLabel#ATA {
        font-size: 12px; 
        color: white; 
        padding: 4px; 
        border-radius: 2px;
        margin: 4px;
    }
    QLabel#ATA:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(82, 153, 224),
            stop: 1 rgb(52, 123, 193)
        );
    }
    QLabel#ATA:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(82, 153, 224, 0.5),
            stop: 1 rgba(52, 123, 193, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# NVMe Badge Stylesheet
nvme_badge = """ 
    QLabel#NVMe {
        font-size: 12px; 
        color: white; 
        padding: 4px; 
        border-radius: 2px;
        margin: 4px;
    }
    QLabel#NVMe:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(166, 110, 181),
            stop: 1 rgb(141, 82, 153)
        );
    }
    QLabel#NVMe:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(166, 110, 181, 0.5),
            stop: 1 rgba(141, 82, 153, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# SCSI Badge Stylesheet
scsi_badge = """ 
    QLabel#SCSI {
        font-size: 12px; 
        color: white; 
        padding: 4px; 
        border-radius: 2px;
        margin: 4px;
    }
    QLabel#SCSI:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(199, 113, 113),
            stop: 1 rgb(174, 78, 78)
        );
    }
    QLabel#SCSI:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(199, 113, 113, 0.5),
            stop: 1 rgba(174, 78, 78, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# SSD Badge Stylesheet
ssd_badge = """ 
    QLabel#SSD {
        font-size: 12px; 
        color: white; 
        padding: 4px; 
        border-radius: 2px;
        margin: 4px;
    }
    QLabel#SSD:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(133, 125, 204),
            stop: 1 rgb(78, 66, 163)
        );
    }
    QLabel#SSD:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(133, 125, 204, 0.5),
            stop: 1 rgba(78, 66, 163, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# HDD Badge Stylesheet
hdd_badge = """ 
    QLabel#HDD {
        font-size: 12px; 
        color: white; 
        padding: 4px; 
        border-radius: 2px;
        margin: 4px;
    }
    QLabel#HDD:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(213, 164, 57),
            stop: 1 rgb(191, 136, 31)
        );
    }
    QLabel#HDD:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(213, 164, 57, 0.5),
            stop: 1 rgba(191, 136, 31, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# Information Badge Stylesheet (Blue)
information_badge = """
    QLabel {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(82, 153, 224),
            stop: 1 rgb(52, 123, 193)
        );
        font-size: 11px; 
        color: white; 
        padding: 4px; 
        border-radius: 2px;
    }
    QLabel:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(82, 153, 224),
            stop: 1 rgb(52, 123, 193)
        );
    }
    QLabel:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(82, 153, 224, 0.5),
            stop: 1 rgba(52, 123, 193, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# Defect Badge Stylesheet (Yellow)
defect_badge = """
    QLabel {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(213, 164, 57),
            stop: 1 rgb(191, 136, 31)
        );
        font-size: 11px; 
        color: white; 
        padding: 4px; 
        border-radius: 2px;
    }
    QLabel:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(213, 164, 57),
            stop: 1 rgb(191, 136, 31)
        );
    }
    QLabel:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(213, 164, 57, 0.5),
            stop: 1 rgba(191, 136, 31, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# Warning Badge Stylesheet (Red)
warning_badge = """
    QLabel {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(199, 113, 113),
            stop: 1 rgb(174, 78, 78)
        );
        font-size: 11px; 
        color: white; 
        padding: 4px; 
        border-radius: 2px;
    }
    QLabel:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(199, 113, 113),
            stop: 1 rgb(174, 78, 78)
        );
    }
    QLabel:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(199, 113, 113, 0.5),
            stop: 1 rgba(174, 78, 78, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# Utility Label Stylesheet (Purple)
utility_badge = """
    QLabel {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(166, 110, 181),
            stop: 1 rgb(141, 82, 153)
        );
        font-size: 11px; 
        color: white; 
        padding: 4px; 
        border-radius: 2px;
    }
    QLabel:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(166, 110, 181),
            stop: 1 rgb(141, 82, 153)
        );
    }
    QLabel:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(166, 110, 181, 0.5),
            stop: 1 rgba(141, 82, 153, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# Pass Badge Stylesheet
pass_badge = """
    QLabel {
        font-size: 12px; 
        color: white; 
        padding: 5px; 
        border-radius: 2px;
        margin: 5px;
    }
    QLabel:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(81, 150, 104),
            stop: 1 rgb(81, 180, 120)
        );
    }
    QLabel:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(81, 150, 104, 0.5),
            stop: 1 rgba(81, 180, 120, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# Pending Badge Stylesheet
pending_badge = """
    QLabel {
        font-size: 12px; 
        color: white; 
        padding: 5px; 
        border-radius: 2px;
        margin: 5px;
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(82, 153, 224),
            stop: 1 rgb(52, 123, 193)
        );
    }
"""

# Cancelled Badge Stylesheet
cancelled_badge = """
    QLabel {
        font-size: 12px; 
        color: white; 
        padding: 5px; 
        border-radius: 2px;
        margin: 5px;
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(255, 140, 0), /* Darker orange */
            stop: 1 rgb(255, 102, 0)
        );
    }
"""

# Fail Badge Stylesheet
failed_badge = """
    QLabel {
        font-size: 12px; 
        color: white; 
        padding: 5px; 
        border-radius: 2px;
        margin: 5px;
    }
    QLabel:enabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(199, 113, 113),
            stop: 1 rgb(174, 78, 78)
        );
    }
    QLabel:disabled {
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgba(199, 113, 113, 0.5),
            stop: 1 rgba(174, 78, 78, 0.5)
        );
        color: rgba(255, 255, 255, 0.5);
    }
"""

# Pending Progress Bar Stylesheet
pending_progress_bar = """
    QProgressBar{
        color: white;
        background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 #404040, stop:1 #333333);
        border-style: none;
        text-align: center;
        font-size: 12px;
        margin-top: 2px;
        margin: 5px;
    }

    QProgressBar::chunk {
        background-color: rgba(100,149,237, 0.8);
        border-style: none;
    }
"""

# Pass Progress Bar
pass_progress_bar = """
    QProgressBar{
        border-style: none;
        border-radius: 10px;
        text-align: center;
        font-size: 12px;
        margin: 5px;
        color: white;
    }

    QProgressBar::chunk {
        background-color: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(81, 150, 104),
            stop: 1 rgb(81, 180, 120)
        );
        border-style: none;
    }
"""

# Fail Progress Bar
failed_progress_bar = """
    QProgressBar{
        border-style: none;
        border-radius: 10px;
        text-align: center;
        font-size: 12px;
        margin: 5px;
        color: white;
    }

    QProgressBar::chunk {
        background-color: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(199, 113, 113),
            stop: 1 rgb(174, 78, 78)
        );
        border-style: none;
    }
"""

# Yellow Progress Bar
yellow_progress_bar = """
    QProgressBar{
        background-color: qlineargradient(spread:repeat, x1:1, y1:0, x2:1, y2:1, stop:0 #404040, stop:1 #333333);
        border-style: none;
        border-radius: 10px;
        text-align: center;
        font-size: 12px;
        margin: 5px;
        color: white;
    }

    QProgressBar::chunk {
        background-color: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 rgb(213, 164, 57),
            stop: 1 rgb(213, 170, 70)
        );
        border-style: none;
    }
"""

# Predicted to Fail Tooltip
predicted_to_fail_tooltip = """
<html>
    <body>
        <p><strong>S.M.A.R.T - Predicted to Fail</strong></p>
        <p>This S.M.A.R.T failure prediction indicates that the hard drive is likely to fail soon.</p>
        <p>When this prediction occurs, it's crucial to take immediate action to backup important data and replace the hardware to prevent data loss.</p>
        <p>Ignoring this warning may lead to sudden data loss and system downtime.</p>
        <p>It's recommended to consult with a professional technician for further assessment and hardware replacement.</p>
        <p>This is a critical parameter. Degradation of this parameter may indicate imminent drive failure. Urgent data backup and hardware replacement is recommended.</p>
    </body>
</html>
"""

# Reallocated Sectors Tooltip
reallocated_sectors_tooltip = """
<html>
    <body>
        <p><strong>Attribute 5 - Reallocated Sector Count</strong></p>
        <p>This S.M.A.R.T parameter is a critical parameter and indicates the current count of reallocated sectors.</p>
        <p>When the drive finds a read/write/verification error, it marks this sector as "reallocated" and transfers data to a special reserved area (spare area).</p>
        <p>This process is also known as remapping and "reallocated" sectors are called remaps. </p>
        <p>This is why, on a modern hard disks, you will not see "bad blocks" while testing the surface - all bad blocks are hidden in reallocated sectors.</p>
        <p>However, the more sectors that are reallocated, the more a sudden decrease (up to 10% and more) can be noticed in the disk read/write speed.</p>
        <p>This is a critical parameter. Degradation of this parameter may indicate imminent drive failure. Urgent data backup and hardware replacement is recommended.</p>
    </body>
</html>
"""

# Pending Sectors Tooltip
pending_sectors_tooltip = """
<html>
    <body>
        <p><strong>Attribute 197 - Current Pending Sector Count</strong></p>
        <p>This S.M.A.R.T parameter is a critical parameter and indicates the current count of unstable sectors (waiting for remapping).</p>
        <p>The raw value of this attribute indicates the total number of sectors waiting for remapping.</p>
        <p>Later, when some of these sectors are read successfully, the value is decreased.</p>
        <p>If errors still occur when reading some sector, the hard drive will try to restore the data, transfer it to the reserved disk area (spare area) and mark this sector as remapped.</p>
        <p>This is a critical parameter. Degradation of this parameter may indicate imminent drive failure. Urgent data backup and hardware replacement is recommended.</p>
    </body>
</html>
"""

# Uncorrectable Errors Tooltip
uncorrectable_errors_tooltip = """
<html>
    <body>
        <p><strong>Attribute 198 - Offline Uncorrectable Sector Count</strong></p>
        <p>This S.M.A.R.T parameter is a critical parameter and indicates the quantity of uncorrectable errors.</p>
        <p>The raw value of this attribute indicates the total number of uncorrectable errors when reading/writing a sector.</p>
        <p>This value shows count of errors detected during offline scan of a disk. </p>
        <p>When idling, a modern disk starts to test itself, the process known as offline scan, in order to detect possible defects in rarely used surface areas.</p>
        <p>This is a critical parameter. Degradation of this parameter may indicate imminent drive failure. Urgent data backup and hardware replacement is recommended.</p>
    </body>
</html>
"""

# Brands List
known_brands_list = [
    # 2-Power
    "2-POWER",
    "2-Power",
    "2-power",
    # ADATA
    "ADATA",
    "Adata",
    "adata",
    # Corsair
    "CORSAIR",
    "Corsair",
    "corsair",
    # Crucial
    "CRUCIAL",
    "Crucial",
    "crucial",
    # Fujitsu
    "FUJITSU",
    "Fujitsu",
    "fujitsu",
    # Gigabyte
    "GIGABYTE",
    "Gigabyte",
    "gigabyte",
    # Hitachi
    "HITACHI",
    "Hitachi",
    "hitachi",
    # IBM
    "IBM-ESXS",
    "IBM-Esxs",
    "ibm-esxs",
    # Intel
    "INTEL",
    "Intel",
    "intel",
    # Intenso
    "INTENSO",
    "Intenso",
    "intenso",
    # KingFast
    "KINGFAST",
    "Kingfast",
    "kingfast",
    # Kingston
    "KINGSTON",
    "Kingston",
    "kingston",
    # Kioxia
    "KIOXIA",
    "Kioxia",
    "kioxia",
    # Lexar
    "LEXAR",
    "Lexar",
    "lexar",
    # Lenovo
    "LENOVO-X",
    "Lenovo-X",
    "lenovo-x",
    # LITEON
    "LITEON",
    "Liteon",
    "liteon",
    # Maxtor
    "MAXTOR",
    "Maxtor",
    "maxtor",
    # Micron
    "MICRON",
    "Micron",
    "micron",
    # NetApp
    "NETAPP",
    "NetApp",
    "netapp",
    # Ortial
    "ORTIAL",
    "Ortial",
    "ortial",
    # Patriot
    "PATRIOT",
    "Patriot",
    "patriot",
    # Plextor
    "PLEXTOR",
    "Plextor",
    "plextor",
    # PLIANT
    "PLIANT",
    "Pliant",
    "pliant",
    # Pioneer
    "PIONEER",
    "Pioneer",
    "pioneer",
    # SanDisk
    "SANDISK",
    "SanDisk",
    "Sandisk",
    "sandisk",
    # Samsung
    "SAMSUNG",
    "Samsung",
    "samsung",
    # Seagate
    "SEAGATE",
    "Seagate",
    "seagate",
    # SK Hynix
    "SK HYNIX",
    "SK hynix",
    "sk hynix",
    # SMI
    "SMI",
    "Smi",
    "smi",
    # Sony
    "SONY",
    "Sony",
    "sony",
    # Super Talent
    "SUPER TALENT",
    "Super Talent",
    "SuperTalent",
    "super talent",
    # Silicon Power CC
    "SPCC",
    "Spcc",
    "spcc",
    # Toshiba
    "TOSHIBA",
    "Toshiba",
    "toshiba",
    # Transcend
    "TRANSCEND",
    "Transcend",
    "transcend",
    # Western Digital
    "WESTERN DIGITAL",
    "Western Digital",
    "western digital",
    "WDC",
    "wdc",
    "WD",
    "wd",
    # Dell
    "DELL",
    "Dell",
    "dell",
    # EMC
    "EMC",
    "Emc",
    "emc",
    # HGST
    "HGST",
    "Hgst",
    "hgst",
    # HPE
    "HPE",
    "Hpe",
    "hpe",
    # HP
    "HP",
    "Hp",
    "hp",
    # IBM
    "IBM",
    "Ibm",
    "ibm",
    # PNY
    "PNY",
    "Pny",
    "pny",
]

# None
none = "NONE"
error = "ERROR"
passed = "PASS"
failed = "FAIL"
ongoing = "ONGOING"
cancelled = "CANCELLED"

# Grades
grade_a = "A"
grade_b = "B"
grade_c = "C"
grade_d = "D"
grade_e = "E"
grade_f = "F"
grade_u = "U"

# Percents
percent_0 = 0
percent_25 = 25
percent_50 = 50
percent_75 = 75
percent_100 = 100

# Thresholds
CDI_EXPECTED_SMART_RESULT = "Pass"
CDI_EXPECTED_SMART_SELF_TEST_RESULT = "Pass"
CDI_MAXIMUM_REALLOCATED_SECTORS = 10
CDI_MAXIMUM_PENDING_SECTORS = 10
CDI_MAXIMUM_UNCORRECTABLE_ERRORS = 10
CDI_MAXIMUM_SSD_PERCENTAGE_USED = 100
CDI_MINIMUM_SSD_AVAILABLE_SPARE = 97

# Commands
sleep_now = "rtcwake -m mem -s 10".split()
reboot_now = "reboot now".split()
shutdown_now = "shutdown now".split()

# Debug
DEBUG = False

# Megabyte
MEGABYTE = 1048576
