#
# Copyright (c) 2026 Circular Drive Initiative.
#
# This file is part of CDI Health.
# See https://github.com/circulardrives/cdi-grading-tool/ for further info.
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
"""String helpers for CDI Health."""

from __future__ import annotations


def clean_string(string: str) -> str:
    """
    Normalize whitespace and underscores in a string.

    :param string: string to be cleaned
    :return: cleaned string
    """
    cleaned_string = string.strip()
    cleaned_string = cleaned_string.replace("_", " ")
    cleaned_string = " ".join(cleaned_string.split())
    return cleaned_string
