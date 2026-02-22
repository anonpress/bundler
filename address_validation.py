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
import sys
from typing import List

import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from address import Address
from config import Config
from opencart_db import Database, OrderStatus


class Validator:
    TOKEN_URL = 'https://apis.usps.com/oauth2/v3/token'
    ADDRESS_URL = 'https://apis.usps.com/addresses/v3/address'
    GOOD_MATCH_CODE = '31'

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.client = BackendApplicationClient(client_id=Config.usps_consumer_key)
        self.usps = OAuth2Session(client=self.client)
        self.usps.fetch_token(token_url=self.TOKEN_URL, client_id=Config.usps_consumer_key,
                              client_secret=Config.usps_consumer_secret, include_client_id=True)

    def validate(self, addresses: List[Address]) -> List[Address | None]:
        """
        Get the validated address from USPS.
        :param addresses: A list of customer-provided addresses.
        :return: A list of validated address, or None for errors.
        """
        return [self.__validate(address) for address in addresses]

    def __validate(self, address: Address) -> Address | None:
        if self.dry_run:
            print(f'Validating address: {address}')
        try:
            res = self.usps.get(self.ADDRESS_URL, params={
                'streetAddress': address.address1.strip(),
                'secondaryAddress': address.address2.strip(),
                'city': address.city.strip(),
                'state': address.state.strip(),
                'ZIPCode': address.zip.strip()[0:5],
            }, headers={
                'Accept': 'application/json',
            })
            if res.status_code != 200:
                print(f'non-200 response: {res}', file=sys.stderr)
                return None
            json = res.json()
            if self.dry_run:
                print(f'Response from USPS: {json}')
        except requests.exceptions.RequestException as e:
            print(f'Request exception: {e}', file=sys.stderr)
            return None

        if any(match['code'] == self.GOOD_MATCH_CODE for match in json['matches']):
            return Address(
                json['address']['streetAddress'] or json['address']['streetAddress'],
                json['address']['secondaryAddress'] or json['address']['urbanization'],
                json['address']['cityAbbreviation'] or json['address']['city'],
                json['address']['state'],
                f'{json['address']['ZIPCode']}-{json['address']['ZIPPlus4']}' if json['address']['ZIPPlus4'] else
                json['address']['ZIPCode']
            )

        print(json['corrections'], file=sys.stderr)
        return None


def main(dry_run=False):
    db = Database(Config.db_host, Config.db_user, Config.db_pass, Config.db_name)
    v = Validator(dry_run)
    orders = db.get_orders_with_status(OrderStatus.PROCESSING, OrderStatus.PROCESSING_UNPAID, OrderStatus.FAILED, OrderStatus.FAILED_UNPAID)
    addresses = v.validate([db.get_order_address(order) for order in orders])
    is_good = True
    for order, address in zip(orders, addresses):
        print(f'Order {order['order_id']}: address {'NOT ' if address is None else ''} validated')
        order_status = db.get_order_status(order)
        if address is None and order_status not in (OrderStatus.FAILED, OrderStatus.FAILED_UNPAID):
            is_good = False
        if address is not None:
            if dry_run:
                print(f'Validated address: {address}')
            db.set_order_address(order, address)
        if order_status in (OrderStatus.PROCESSING, OrderStatus.FAILED):
            order = db.set_order_status(order,
                                        OrderStatus.FAILED if address is None
                                        else OrderStatus.VALIDATED)
        elif order_status in (OrderStatus.PROCESSING_UNPAID, OrderStatus.FAILED_UNPAID):
            order = db.set_order_status(order,
                                        OrderStatus.FAILED_UNPAID if address is None
                                        else OrderStatus.VALIDATED_UNPAID)
        db.update_order(order, dry_run)
    if not is_good:
        exit(1337)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser('Validate addresses in OpenCart database.')
    parser.add_argument('--dry-run', '-n', action='store_true')
    args = parser.parse_args()
    main(args.dry_run)
