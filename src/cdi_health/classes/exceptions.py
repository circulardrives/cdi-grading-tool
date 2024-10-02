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
Circular Drive Initiative - Exceptions

@language    Python 3.12
@framework   PySide 6
@version     0.0.1
"""


# TODO: manage via isort
from __future__ import annotations


class CDIException(Exception):
    """
    Command Exception
    """

    def __init__(self, message):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message


class CommandException(Exception):
    """
    Command Exception
    """

    def __init__(self, message):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message


class ConfigurationException(Exception):
    """
    Configuration Exception
    """

    def __init__(self, message):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message


class SystemException(Exception):
    """
    System Exception
    """

    def __init__(self, message):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message


class DevicesException(Exception):
    def __init__(self, message):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message


class NoDevicesDetectedException(Exception):
    """
    No Devices Detected Exception
    """

    def __init__(self, message):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message


class NotCertifiedForReuseException(Exception):
    """
    Not Certified for Reuse Exception
    """

    def __init__(self, message):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message


"""
Process Exceptions
"""


class Cancelled(Exception):
    """
    Device Exception
    """

    def __init__(self, message, reason):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message
        self.reason = reason


class DeviceLost(Exception):
    """
    Device Exception
    """

    def __init__(self, message, reason):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message
        self.reason = reason


class DeviceFail(Exception):
    """
    Device Exception
    """

    def __init__(self, message, reason):
        """
        Initialize
        :param message:
        """

        # Set Message
        self.message = message
        self.reason = reason


class SMARTFail(Exception):
    """
    S.M.A.R.T Exception
    """

    def __init__(self, reason):
        """
        Initialize
        :param reason:
        """

        # Set Message
        self.reason = reason


class SMARTSelfTestFail(Exception):
    """
    S.M.A.R.T Historic Self-test Fail Exception
    """

    def __init__(self, reason):
        """
        Initialize
        :param reason:
        """

        # Set Message
        self.reason = reason


class SMARTHistoricSelfTestFail(Exception):
    """
    S.M.A.R.T Historic Self-test Fail Exception
    """

    def __init__(self, reason):
        """
        Initialize
        :param reason:
        """

        # Set Message
        self.reason = reason


class ReallocatedSectorsExceedsThreshold(Exception):
    """
    Reallocated Sectors Exceeds Threshold Exception
    """

    def __init__(self, reason):
        """
        Initialize
        :param reason:
        """

        # Set Message
        self.reason = reason


class PendingSectorsExceedsThreshold(Exception):
    """
    Pending Sectors Exceeds Threshold Exception
    """

    def __init__(self, reason):
        """
        Initialize
        :param reason:
        """

        # Set Message
        self.reason = reason


class SSDUsedPercentageExceedsThreshold(Exception):
    """
    SSD Used Percentage Exceeds Threshold Exception
    """

    def __init__(self, reason):
        """
        Initialize
        :param reason:
        """

        # Set Message
        self.reason = reason