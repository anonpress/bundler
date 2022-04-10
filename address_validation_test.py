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

import pytest

from config import Config
from address_validation import Address, Validator


@pytest.fixture
def invalid_address():
    return Address('1 FAKEDR', '', 'Malo', 'WA', '99150')


@pytest.fixture
def input_address():
    return Address('1658 n milwaukee', '100-2883', 'Chicago', 'IL', '60647')


@pytest.fixture
def input_address_2():
    return Address('1600 amphitheatre parkway', '', 'Mountain View', 'CA', '')


@pytest.fixture
def output_address():
    return Address('1658 N MILWAUKEE AVE # 100-2883', '', 'CHICAGO', 'IL', '60647-6905')


@pytest.fixture
def output_address_2():
    return Address('1600 AMPHITHEATRE PKWY', '', 'MOUNTAIN VIEW', 'CA', '94043-1351')


@pytest.fixture
def valid_response():
    return """<?xml version="1.0" encoding="UTF-8"?>
<AddressValidateResponse><Address ID="0"><Address2>1658 N MILWAUKEE AVE # 100-2883</Address2><City>CHICAGO</City><State>IL</State><Zip5>60647</Zip5><Zip4>6905</Zip4><ReturnText>Default address: The address you entered was found but more information is needed (such as an apartment, suite, or box number) to match to a specific address.</ReturnText></Address></AddressValidateResponse>"""


@pytest.fixture
def invalid_response():
    return """<?xml version="1.0" encoding="UTF-8"?>
<AddressValidateResponse><Address ID="0"><Error><Number>-2147219401</Number><Source>clsAMS</Source><Description>Address Not Found.  </Description><HelpFile/><HelpContext/></Error></Address></AddressValidateResponse>"""


def test_validate(requests_mock, input_address, output_address, valid_response):
    requests_mock.get(Validator.ENDPOINT, text=valid_response)
    v = Validator('fake user id')
    assert v.validate([input_address]) == [output_address]


def test_validator_integration(invalid_address, input_address, input_address_2, output_address,
                               output_address_2):
    v = Validator(Config.usps_user)
    assert v.validate([input_address, invalid_address, input_address_2]) == [output_address, None,
                                                                             output_address_2]
