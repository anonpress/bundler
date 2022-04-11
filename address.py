# Copyright 2022 Google LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from typing import NamedTuple


class Address(NamedTuple):
    address1: str
    address2: str
    city: str
    state: str
    zip: str

    def __eq__(self, other):
        return self.address1 == other.address1 and self.address2 == other.address2 and \
               self.city == other.city and self.state == other.state and self.zip == other.zip
