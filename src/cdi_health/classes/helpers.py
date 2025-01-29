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
Circular Drive Initiative - Helpers

@language    Python 3.12
@framework   PySide 6
@version     0.0.1
"""

from __future__ import annotations

# Modules
import logging
import os
import random


class Helper:
    """
    Helper Class
    """

    def __init__(self):
        pass

    """
    String Helpers
    """

    @staticmethod
    def capitalize_first_letter(string: str) -> str:
        """
        Capitalize
        :param string: string to be capitalized
        :return: string capitalized
        """

        # Return String
        return string.capitalize()

    @staticmethod
    def convert_to_binary(number: int) -> str:
        """
        Convert a decimal number to binary.
        :param number: number to be converted to binary sequence
        :return: binary representation of number
        """

        # Return String
        return bin(number)

    @staticmethod
    def convert_to_hexadecimal(number):
        """
        Convert a decimal number to hexadecimal.
        :param number: number to be converted to hexadecimal value
        :return: hexadecimal representation of number
        """

        # Return String
        return hex(number)

    @staticmethod
    def count_vowels(string: str) -> int:
        """
        Count Vowels in String
        """

        # Return Count of Vowels
        return sum(1 for char in string if char.lower() in "aeiou")

    @staticmethod
    def clean_string(string: str) -> str:
        """
        Clean string
        :param string: string to be cleaned
        :return: cleaned string
        """

        # Remove Whitespaces
        cleaned_string = string.strip()

        # Replace Underscores
        cleaned_string = cleaned_string.replace("_", " ")

        # Remove Extra Spaces
        cleaned_string = " ".join(cleaned_string.split())

        # Return Cleaned String
        return cleaned_string

    @staticmethod
    def remove_whitespaces_from_string(string: str) -> str:
        """
        Remove Whitespaces
        :param string: string to be stripped of whitespace
        :return: string without whitespaces
        """

        # Return String
        return "".join(string.split())

    @staticmethod
    def reverse_string(string: str) -> str:
        """
        Reverse
        :param string: string to be reversed
        :return: string reversed
        """

        # Return String
        return string[::-1]

    @staticmethod
    def is_palindrome(string: str) -> bool:
        """
        Check if a string is a palindrome
        :param string: string to be checked for palindrome
        :return: bool
        """

        # Clean String
        cleaned_string = "".join(char.lower() for char in string if char.isalnum())

        # Return Checked String
        return cleaned_string == cleaned_string[::-1]

    """
    Number Helpers
    """

    @staticmethod
    def factorial(number: int) -> int:
        """
        Calculate the factorial of a number.
        :param number: number to be factored
        :return: factorial of number
        """

        # If Zero
        if number == 0:
            # Return 1
            return 1

        # Return Factorial
        return number * Helper.factorial(number - 1)

    @staticmethod
    def fibonacci_sequence(n: int) -> list:
        """
        Generate the Fibonacci sequence up to the nth term.
        :param n: nth term
        :return: Fibonacci sequence
        """

        # Sequence
        sequence = [0, 1]

        # While Sequence
        while len(sequence) < n:
            # Append
            sequence.append(sequence[-1] + sequence[-2])

        # Return Fibonacci Sequence
        return sequence

    @staticmethod
    def generate_random_number_within_range(start, end):
        """
        Generate a random number within a given range.
        """

        # Return Random Number
        return random.randint(start, end)

    @staticmethod
    def is_prime(number: int) -> bool:
        """
        Check if a number is prime
        :param number: number to be checked
        :return: bool
        """

        # If <= to 1
        if number <= 1:
            # Return False
            return False

        # Loop Numbers
        for i in range(2, int(number**0.5) + 1):
            # If Number is Divisble by I
            if number % i == 0:
                # Return False
                return False

        # Return True
        return True

    @staticmethod
    def sum_of_digits(number: int) -> int:
        """
        Calculate the sum of digits of a number.
        :param number: number to be summed
        :return: sum of digits
        """

        # Return Sum of the Digits
        return sum(int(digit) for digit in str(number) if digit.isdigit())


class Logger:
    """
    Logger Class
    """

    def __init__(self, name, log_level=logging.INFO, log_to_console=True, log_to_file=False, log_file_path="logs"):
        """
        Constructor
        :param name: Log Name
        :param log_level: Logging Level - Defaults to INFO
        :param log_to_console: Print to the Console - Defaults to True
        :param log_to_file: Save to a File - Defaults to False
        :param log_file_path: Logging Path - Defaults to 'logs'
        """

        # Get Logger
        self.logger = logging.getLogger(name)

        # Set Level
        self.logger.setLevel(log_level)

        # Format Logger
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # If Log to Console
        if log_to_console:
            # Create Stream Handler
            ch = logging.StreamHandler()

            # Set Level
            ch.setLevel(log_level)

            # Set Format
            ch.setFormatter(formatter)

            # Add Handler
            self.logger.addHandler(ch)

        # If Log to File
        if log_to_file:
            # If File Path doesn't exist
            if not os.path.exists(log_file_path):
                # Make Directory
                os.makedirs(log_file_path)

            # Create File Handler
            fh = logging.FileHandler(os.path.join(log_file_path, f"{name}.log"))

            # Set Level
            fh.setLevel(log_level)

            # Set Formatter
            fh.setFormatter(formatter)

            # Add Handler
            self.logger.addHandler(fh)

    def debug(self, message):
        """
        Debug Logger
        :param message:
        :return:
        """

        # Debug Log
        self.logger.debug(message)

    def info(self, message):
        """
        Info Logger
        :param message:
        :return:
        """

        # Info Log
        self.logger.info(message)

    def warning(self, message):
        """
        Warning Logger
        :param message:
        :return:
        """

        # Warning Log
        self.logger.warning(message)

    def error(self, message):
        """
        Error Logger
        :param message:
        :return:
        """

        # Error Log
        self.logger.error(message)

    def critical(self, message):
        """
        Critical
        :param message:
        :return:
        """

        # Critical Log
        self.logger.critical(message)


class Report(dict):
    """
    Report Class
    """

    def __init__(self) -> None:
        """
        Initialize
        """

        # Initialize Parent
        super().__init__()
