#
# Copyright (c) 2025 Circular Drive Initiative.
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
"""

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
