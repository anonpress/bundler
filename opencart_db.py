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
from typing import List, Optional

import mysql.connector

from address import Address


class Database:
    def __init__(self, host, user, password, db):
        self.cnx = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db,
            raise_on_warnings=True
        )
        self.cursor = self.cnx.cursor(dictionary=True)

    def __del__(self):
        try:
            self.cursor.close()
            self.cnx.close()
        except ReferenceError:
            pass

    STATUS_PENDING = 1
    STATUS_PROCESSED = 15
    STATUS_SHIPPED = 3
    STATUS_COMPLETE = 5
    STATUS_VALIDATED = 17
    STATUS_FAILED = 18
    COUNTRY_ID_US = 223

    SELECT_ORDER_QUERY = """
            SELECT oc_order.*, oc_zone.code AS shipping_state FROM oc_order 
            LEFT JOIN oc_zone ON oc_order.shipping_zone_id = oc_zone.zone_id 
            WHERE order_status_id=%s
            """

    SELECT_STATE_QUERY = """
            SELECT zone_id, name FROM oc_zone WHERE country_id=%s AND code=%s
            """

    SELECT_CONTENTS_QUERY = """
            SELECT model, quantity FROM oc_order_product WHERE order_id=%s
            """

    def get_orders_with_status(self, status: int) -> List[dict]:
        self.cursor.execute(self.SELECT_ORDER_QUERY, (status,))
        return self.cursor.fetchall()

    def get_code_for_state(self, abbr: str) -> dict:
        self.cursor.execute(self.SELECT_STATE_QUERY, (Database.COUNTRY_ID_US, abbr))
        return self.cursor.fetchone()

    def get_order_contents(self, order_id: int) -> dict:
        self.cursor.execute(self.SELECT_CONTENTS_QUERY, (order_id,))
        return {item['model']: item['quantity'] for item in self.cursor.fetchall()}

    @staticmethod
    def get_order_address(order: dict) -> Address:
        return Address(
            order['shipping_address_1'],
            order['shipping_address_2'],
            order['shipping_city'],
            order['shipping_state'],
            order['shipping_postcode']
        )

    def set_order_address(self, order: dict, address: Optional[Address]) -> dict:
        order['shipping_address_1'] = address.address1
        order['shipping_address_2'] = address.address2
        order['shipping_city'] = address.city
        order['shipping_postcode'] = address.zip
        if order['shipping_state'] != address.state:
            new_state = self.get_code_for_state(address.state)
            order['shipping_state'] = address.state
            order['shipping_zone_id'] = new_state['zone_id']
            order['shipping_zone'] = new_state['name']
        return order

    @staticmethod
    def set_order_status(order: dict, status: int) -> dict:
        order['order_status_id'] = status
        return order

    def update_order(self, order: dict) -> None:
        self.cursor.execute(
            f"UPDATE oc_order SET {', '.join(f'`{k}`=%s' for k in order if k != 'shipping_state')}"
            ' WHERE order_id=%s',
            [*[v for k, v in order.items() if k != 'shipping_state'], order['order_id']])
