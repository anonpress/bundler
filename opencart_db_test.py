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
import re
import unittest
from unittest.mock import patch, MagicMock

from address_validation import Address
from opencart_db import Database

address_before = Address('Address 2-1', 'Address 2-2', 'City 2', 'GA', '10101')

address_after = Address('Address 2-1', '', 'New City', 'WA', '10101-2345')

orders_before = [
    {
        'order_id':           1,
        'order_status_id':    Database.STATUS_PENDING,
        'shipping_address_1': 'Address 1-1',
        'shipping_address_2': 'Address 1-2',
        'shipping_city':      'City 1',
        'shipping_postcode':  '01010',
        'shipping_zone':      'Colorado',
        'shipping_zone_id':   3625,
        'shipping_state':     'CO',
    },
    {
        'order_id':           2,
        'order_status_id':    Database.STATUS_PENDING,
        'shipping_address_1': 'Address 2-1',
        'shipping_address_2': 'Address 2-2',
        'shipping_city':      'City 2',
        'shipping_postcode':  '10101',
        'shipping_zone':      'Georgia',
        'shipping_zone_id':   3631,
        'shipping_state':     'GA',
    },
]

orders_after = [
    {
        'order_id':           1,
        'order_status_id':    Database.STATUS_PENDING,
        'shipping_address_1': 'Address 1-1',
        'shipping_address_2': 'Address 1-2',
        'shipping_city':      'City 1',
        'shipping_postcode':  '01010',
        'shipping_zone':      'Colorado',
        'shipping_zone_id':   3625,
        'shipping_state':     'CO',
    },
    {
        'order_id':           2,
        'order_status_id':    Database.STATUS_PENDING,
        'shipping_address_1': 'Address 2-1',
        'shipping_address_2': '',
        'shipping_city':      'New City',
        'shipping_postcode':  '10101-2345',
        'shipping_zone':      'Washington',
        'shipping_zone_id':   3674,
        'shipping_state':     'WA',
    },
]

washington = {'name': 'Washington', 'zone_id': 3674}


class QueryMatcher(str):
    def __eq__(self, other):
        return re.sub(r'\W+', ' ', self.strip().upper()) == re.sub(r'\W+', ' ',
                                                                   other.strip().upper())


class TestOpencartDb(unittest.TestCase):
    @patch('mysql.connector.connect')
    def setUp(self, mock_connector) -> None:
        self.mock = MagicMock()  # mock cursor
        mock_cnx = MagicMock()
        mock_cnx.cursor = MagicMock(return_value=self.mock)
        mock_connector.return_value = mock_cnx
        self.db = Database('', '', '', '')
        mock_connector.assert_called_once()
        mock_cnx.cursor.assert_called_once_with(dictionary=True)
        self.mock.execute = MagicMock()

    def test_get_orders_with_status(self):
        self.mock.fetchall = MagicMock(return_value=orders_before)
        self.assertEqual(self.db.get_orders_with_status(Database.STATUS_PENDING), orders_before)
        self.mock.execute.assert_called_once_with(QueryMatcher(Database.SELECT_ORDER_QUERY),
                                                  (Database.STATUS_PENDING,))

    def test_get_orders_with_status_no_results(self):
        self.mock.fetchall = MagicMock(return_value=[])
        self.assertEqual(self.db.get_orders_with_status(-1), [])
        self.mock.execute.assert_called_once_with(QueryMatcher(Database.SELECT_ORDER_QUERY), (-1,))

    def test_get_code_for_state(self):
        self.mock.fetchone = MagicMock(return_value=washington)
        self.assertEqual(self.db.get_code_for_state('WA'), washington)
        self.mock.execute.assert_called_once_with(QueryMatcher(Database.SELECT_STATE_QUERY),
                                                  (Database.COUNTRY_ID_US, 'WA'))

    def test_get_code_for_state_no_results(self):
        self.mock.fetchone = MagicMock(return_value=None)
        self.assertIsNone(self.db.get_code_for_state('XX'))
        self.mock.execute.assert_called_once_with(QueryMatcher(Database.SELECT_STATE_QUERY),
                                                  (Database.COUNTRY_ID_US, 'XX'))

    def test_get_order_address(self):
        self.assertEqual(Database.get_order_address(orders_before[1]), address_before)

    def test_set_order_address(self):
        self.db.get_code_for_state = MagicMock(return_value=washington)
        self.assertEqual(self.db.set_order_address(orders_before[1], address_after),
                         orders_after[1])
        self.db.get_code_for_state.assert_called_once_with('WA')

    def test_set_order_status(self):
        result = Database.set_order_status(orders_before[0], Database.STATUS_PROCESSED)
        expected = orders_before[0]
        expected['order_status_id'] = Database.STATUS_PROCESSED
        self.assertEqual(result, expected)

    def test_update_order(self):
        new = orders_after[1]
        self.db.update_order(new)
        self.mock.execute.assert_called_once_with(QueryMatcher(
            """
            UPDATE oc_order SET `order_id`=%s, `order_status_id`=%s, `shipping_address_1`=%s,
            `shipping_address_2`=%s, `shipping_city`=%s, `shipping_postcode`=%s, `shipping_zone`=%s,
            `shipping_zone_id`=%s WHERE order_id=%s
            """
        ), [new['order_id'], new['order_status_id'], new['shipping_address_1'],
            new['shipping_address_2'], new['shipping_city'], new['shipping_postcode'],
            new['shipping_zone'], new['shipping_zone_id'], new['order_id']])
