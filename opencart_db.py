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
from enum import IntEnum
from typing import List, Dict, Union, Optional, Set

import mysql.connector
from mysql.connector import DatabaseError

from address import Address

OrderInfo = Dict[str, Union[str, int]]
ZoneInfo = Dict[str, Union[str, int]]  # keys are zone_id and name
Items = Dict[str, int]  # sku -> qty


class OrderStatus(IntEnum):
    PENDING = 1
    PROCESSED = 15
    SHIPPED = 3
    COMPLETE = 5
    VALIDATED = 17
    FAILED = 18
    PROCESSING = 2


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

    COUNTRY_ID_US = 223

    SELECT_ORDER_QUERY = """
        SELECT * FROM oc_order WHERE order_id=%s
    """

    SELECT_ORDERS_QUERY = """
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

    def get_order(self, order_id: int) -> Optional[OrderInfo]:
        self.cursor.execute(self.SELECT_ORDER_QUERY, (order_id,))
        return self.cursor.fetchone()

    def get_orders_with_status(self, status: OrderStatus) -> List[OrderInfo]:
        self.cursor.execute(self.SELECT_ORDERS_QUERY, (int(status),))
        return self.cursor.fetchall()

    def get_code_for_state(self, abbr: str, country=COUNTRY_ID_US) -> Optional[ZoneInfo]:
        self.cursor.execute(self.SELECT_STATE_QUERY, (country, abbr))
        return self.cursor.fetchone()

    def get_order_contents(self, order_id: int) -> Items:
        self.cursor.execute(self.SELECT_CONTENTS_QUERY, (order_id,))
        return {item['model']: item['quantity'] for item in self.cursor.fetchall()}

    @staticmethod
    def get_order_address(order: OrderInfo) -> Address:
        return Address(
            order['shipping_address_1'],
            order['shipping_address_2'],
            order['shipping_city'],
            order['shipping_state'],
            order['shipping_postcode']
        )

    def set_order_address(self, order: OrderInfo, address: Address) -> OrderInfo:
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
    def set_order_status(order: OrderInfo, status: OrderStatus) -> OrderInfo:
        order['order_status_id'] = int(status)
        return order

    def update_order(self, order: OrderInfo) -> None:
        try:
            self.cursor.execute(
                f"UPDATE oc_order SET {', '.join(f'`{k}`=%s' for k in order if k != 'shipping_state')}"
                ' WHERE order_id=%s',
                [*[v for k, v in order.items() if k != 'shipping_state'], order['order_id']])
        except DatabaseError as err:
            print(f'Warning updating order {order["order_id"]}: {err.msg}')

    def customer_ids(self) -> Set[int]:
        self.cursor.execute('SELECT customer_id FROM oc_customer')
        return {customer['customer_id'] for customer in self.cursor.fetchall()}

    def order_ids(self) -> Set[int]:
        self.cursor.execute('SELECT order_id FROM oc_order')
        return {order['order_id'] for order in self.cursor.fetchall()}

    def get_country(self, country_code: str) -> ZoneInfo:
        self.cursor.execute(
            'SELECT country_id AS zone_id, name FROM oc_country WHERE iso_code_2 = %s',
            (country_code,))
        return self.cursor.fetchone()
