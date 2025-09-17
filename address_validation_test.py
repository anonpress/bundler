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
import unittest
from unittest.mock import patch, MagicMock

from address import Address
from address_validation import Validator
from config import Config

invalid_address = Address('1 FAKEDR', '', 'Malo', 'WA', '99150')
input_address = Address('1658 n milwaukee', '100-2883', 'Chicago', 'IL', '60647')
input_address_2 = Address('1600 amphitheatre parkway', '', 'Mountain View', 'CA', '')
output_address = Address('1658 N MILWAUKEE AVE # 100-2883', '', 'CHICAGO', 'IL', '60647-6905')
output_address_2 = Address('1600 AMPHITHEATRE PKWY', '', 'MOUNTAIN VIEW', 'CA', '94043-1351')
valid_response = """<?xml version="1.0" encoding="UTF-8"?>
<AddressValidateResponse><Address ID="0"><Address2>1658 N MILWAUKEE AVE # 100-2883</Address2><City>CHICAGO</City><State>IL</State><Zip5>60647</Zip5><Zip4>6905</Zip4><ReturnText>Default address: The address you entered was found but more information is needed (such as an apartment, suite, or box number) to match to a specific address.</ReturnText></Address></AddressValidateResponse>"""
invalid_response = """<?xml version="1.0" encoding="UTF-8"?>
<AddressValidateResponse><Address ID="0"><Error><Number>-2147219401</Number><Source>clsAMS</Source><Description>Address Not Found.  </Description><HelpFile/><HelpContext/></Error></Address></AddressValidateResponse>"""


class TestValidator(unittest.TestCase):
    @patch('requests.get')
    def test_validate(self, mock_get):
        mock_get.return_value = MagicMock()
        mock_get.return_value.text = valid_response
        v = Validator('fake user id')
        self.assertEqual(v.validate([input_address]), [output_address])

    def test_validator_integration(self):
        v = Validator(Config.usps_user)
        self.assertEqual(v.validate([input_address, invalid_address, input_address_2]),
                         [output_address, None, output_address_2])
