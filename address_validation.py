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

import xml.etree.ElementTree as et
from typing import NamedTuple, List, Optional
from xml.sax.saxutils import escape

import requests


class Address(NamedTuple):
    address1: str
    address2: str
    city: str
    state: str
    zip: str

    def __eq__(self, other):
        return self.address1 == other.address1 and self.address2 == other.address2 and \
               self.city == other.city and self.state == other.state and self.zip == other.zip


class Validator:
    def __init__(self, usps_user):
        self.usps_user = usps_user

    ENDPOINT = 'https://secure.shippingapis.com/ShippingAPI.dll'

    def validate(self, addresses: List[Address]) -> List[Optional[Address]]:
        """
        Get the validated address from USPS.
        :param addresses: A list of customer-provided addresses.
        :return: A list of validated address, or None for errors.
        """
        xml = self.__build_xml(addresses)
        res = self.__request(xml)
        return self.__parse_response(res)

    def __build_xml(self, addresses: List[Address]) -> str:
        root = et.Element('AddressValidateRequest')
        root.set('USERID', self.usps_user)
        for index, address in enumerate(addresses):
            a = et.SubElement(root, 'Address')
            a.set('ID', str(index))
            # USPS API swaps address 2 and 1 for some reason.
            et.SubElement(a, 'Address1').text = escape(address.address2.strip())
            et.SubElement(a, 'Address2').text = escape(address.address1.strip())
            et.SubElement(a, 'City').text = escape(address.city.strip())
            et.SubElement(a, 'State').text = escape(address.state.strip())
            et.SubElement(a, 'Zip5').text = escape(address.zip.strip()[0:5])
            zip4 = et.SubElement(a, 'Zip4')
            try:
                zip4.text = escape(address.zip.strip().split('-')[1])
            except IndexError:
                pass
        return et.tostring(root, encoding='unicode')

    @staticmethod
    def __request(xml: str) -> str:
        query = {'API': 'Verify', 'XML': xml}
        return requests.get(Validator.ENDPOINT, params=query).text

    @staticmethod
    def __parse_response(xml: str) -> List[Optional[Address]]:
        results = []
        for result in et.fromstring(xml):
            r = {e.tag: e.text for e in result}
            index = int(result.get('ID'))
            try:
                results.insert(index,
                               Address(r['Address2'], r.get('Address1', ''), r['City'], r['State'],
                                       f"{r['Zip5']}-{r['Zip4']}" if len(r['Zip4']) == 4
                                       else r['Zip5']))
            except KeyError:
                results.insert(index, None)
        return results
