#
# Copyright 2018 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Defines the abstract generator."""
import datetime
from abc import ABC, abstractmethod

from faker import Faker


# pylint: disable=too-few-public-methods
class AbstractGenerator(ABC):
    """Defines a abstract class for generators."""

    def __init__(self, start_date, end_date):
        """Initialize the generator."""
        self.start_date = start_date
        self.end_date = end_date
        self.hours = self._set_hours()
        self.fake = Faker()
        super().__init__()

    def _set_hours(self):
        """Create a list of hours between the start and end dates."""
        hours = []
        if not self.start_date or not self.end_date:
            raise ValueError('start_date and end_date must be date objects.')
        if not isinstance(self.start_date, datetime.datetime):
            raise ValueError('start_date must be a date object.')
        if not isinstance(self.end_date, datetime.datetime):
            raise ValueError('end_date must be a date object.')
        if self.end_date < self.start_date:
            raise ValueError('start_date must be a date object less than end_date.')

        one_hour = datetime.timedelta(minutes=60)
        cur_date = self.start_date
        end_date = self.end_date.replace(hour=23)
        while (cur_date + one_hour) <= end_date:
            cur_hours = {'start': cur_date, 'end': cur_date + one_hour}
            hours.append(cur_hours)
            cur_date = cur_date + one_hour
        return hours

    @staticmethod
    def next_month(in_date):
        """Return the first of the next month from the in_date."""
        dt_first = in_date.replace(day=1)
        dt_up_month = dt_first + datetime.timedelta(days=32)
        dt_next_month = dt_up_month.replace(day=1)
        return dt_next_month

    @abstractmethod
    def _init_data_row(self, start, end):
        """Create a row of data with placeholder for all headers."""
        pass

    @abstractmethod
    def _add_common_usage_info(self, row, start, end):
        """Add common usage information."""
        pass

    @abstractmethod
    def _update_data(self, row, start, end, **kwargs):
        """Update data with generator specific data."""
        pass

    @abstractmethod
    def _generate_hourly_data(self):
        """Create houldy data."""
        pass

    @abstractmethod
    def generate_data(self):
        """Responsibile for generating data."""
        pass
