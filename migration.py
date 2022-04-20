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
import argparse
import csv
from datetime import datetime
from typing import Dict, Union, NamedTuple, Tuple, Optional

from mysql.connector import DatabaseError

from config import Config
from opencart_db import Database, Items, OrderStatus, ZoneInfo

CsvRow = Dict[str, Union[str, bool]]
TrackingInfo = Dict[str, Items]
ItemsAndTotal = Dict[str, Tuple[int, float]]


class OrderData(NamedTuple):
    info: CsvRow
    items: ItemsAndTotal
    tracking: TrackingInfo
    imported: bool


class Migration:
    def __init__(self, arguments):
        self.db = Database(Config.db_host, Config.db_user, Config.db_pass, Config.db_name)
        self.existing_customers = self.db.customer_ids()
        self.existing_orders = self.db.order_ids()
        self.imported_customers = 0
        self.imported_orders = 0
        self.customer_reader = csv.DictReader(args.customers)
        self.order_reader = csv.DictReader(args.orders)
        self.args = arguments
        self.customers: Dict[str, CsvRow] = {}
        for row in self.customer_reader:
            row['imported'] = int(row['contactid']) in self.existing_customers
            self.customers[row['contactid']] = row
        self.zone_info: Dict[str, ZoneInfo] = {}
        self.orders: Dict[str, OrderData] = {}
        for row in self.order_reader:
            orderid = row['orderid']
            if orderid not in self.orders:
                self.orders[orderid] = OrderData(row, {}, {}, int(orderid) in self.existing_orders)
            items = self.orders[orderid].items.get(row['itemid'], (0, 0))
            items = (
                items[0] + int(row['numitems'] or '1'), items[1] + float(row['itemamount'] or '0'))
            self.orders[orderid].items[row['itemid']] = items
            if len(row['trackingcode']) > 1:
                if row['trackingcode'] not in self.orders[orderid].tracking:
                    self.orders[orderid].tracking[row['trackingcode']] = {}
                if row['itemid'] not in self.orders[orderid].tracking[row['trackingcode']]:
                    self.orders[orderid].tracking[row['trackingcode']][row['itemid']] = 0
                self.orders[orderid].tracking[row['trackingcode']][row['itemid']] += int(
                    row['numitems'] or '1')
        print(f'Existing orders: {self.existing_orders}')
        print(f'Existing customers: {self.existing_customers}')
        print(f'Found {len(self.orders)} orders in input file')
        print(f'Found {len(self.customers)} customers in input file')

    item_map: Dict[str, Optional[int]] = {
        '0':         64,
        '':          64,
        'E-CD':      63,
        'XL':        57,
        'SOFT':      54,
        'MI':        50,
        'BARSOFT':   54,
        'ST':        None,
        '000000':    64,
        'E':         58,
        'Study-ST':  59,
        'CAMO':      52,
        'IN':        55,
        'BARMI':     50,
        'BARST':     59,
        'CON':       53,
        'Study-BL':  51,
        'BARWO':     56,
        'BLG':       None,
        'ECD':       58,
        'EPUB':      58,
        'BARFE':     61,
        'BL':        None,
        'STG':       None,
        'Study-BLG': 60,
        'Study-STG': 62,
        'DN':        64,
        'DO':        64,
        'BARBLG':    60,
        'BARSTG':    62,
        'BARCAMO':   52,
        'BARBL':     51,
        'BARXL':     57,
        'FE':        61,
        'WO':        56,
        'BARCON':    53,
    }

    name_map: Dict[str, str] = {
        '0':         'Discount',
        '':          'Miscellaneous',
        'E-CD':      'e-AA CD',
        'XL':        'Extra Large Print',
        'SOFT':      'First Edition - Softcover',
        'MI':        'Mini Edition',
        'BARSOFT':   'First Edition - Softcover Seconds',
        '000000':    'Miscellaneous',
        'E':         'e-AA',
        'Study-ST':  'Study Edition - Burgundy',
        'CAMO':      'Mini Edition - Camo',
        'IN':        'Anonymous Press Index',
        'BARMI':     'Mini Edition - Seconds',
        'BARST':     'Study Edition - Burgundy Seconds',
        'CON':       'Concordance',
        'Study-BL':  'Study Edition',
        'BARWO':     'Study Edition - Softcover',
        'ECD':       'e-AA CD',
        'EPUB':      'ePub Format Big Book',
        'BARFE':     'First Edition - Hardcover Clearance',
        'Study-BLG': 'Study Edition - Black with Gilding',
        'Study-STG': 'Study Edition - Burgundy with Gilding',
        'DN':        'Donation',
        'DO':        'Donation',
        'BARBLG':    'Study Edition - Black with Gilding Seconds',
        'BARSTG':    'Study Edition - Burgundy with Gilding Seconds',
        'BARCAMO':   'Mini Edition - Camo seconds',
        'BARBL':     'Study Edition - Black Seconds',
        'BARXL':     'Extra Large Print Seconds',
        'FE':        'First Edition - Hardcover',
        'WO':        'Study Edition - Softcover',
        'BARCON':    'Concordance Seconds',
    }

    order_status_map: Dict[str, int] = {
        '1':  OrderStatus.PROCESSING,
        '4':  OrderStatus.SHIPPED,
        '6':  OrderStatus.PROCESSED,
        '11': 14,
    }

    def run(self):
        for order in self.orders.values():
            if order.imported or order.info['order_status'] == '7':
                continue
            if args.limit_orders and self.imported_orders == args.limit_orders:
                break
            orderid = int(order.info['orderid'])
            if int(order.info['orderid']) < args.from_order:
                continue
            customerid = order.info['ocustomerid']
            if customerid != '0':
                try:
                    customer = self.customers[customerid]
                    if not customer['imported'] and not self.import_customer(customer):
                        print(f'Skipping order {orderid} due to customer {customerid}')
                        continue
                except KeyError:
                    print(
                        f'Customer {customerid} not found; setting customer for order {orderid} to 0')
            if self.import_order(order.info, self.build_comment(order)):
                self.add_order_items(order)

    @staticmethod
    def build_comment(order: OrderData) -> str:
        def items_string(items: Items):
            return ', '.join(f'{qty} {sku}' for sku, qty in items.items())

        return f"""Imported order {order.info['orderid']}
Order date: {order.info['odate']}
{items_string({k: v[0] for k, v in order.items.items()})}
{'Tracking:' if len(order.tracking) > 0 else 'No tracking available'}
""" + '\n'.join(f'{k} - {items_string(v)}' for k, v in order.tracking.items())

    @staticmethod
    def parse_date(date: str) -> datetime:
        try:
            try:
                return datetime.strptime(date, '%m/%d/%Y %I:%M:%S %p')
            except ValueError:
                return datetime.strptime(date, '%m/%d/%Y')
        except:
            print(f'Error parsing date {date}')
            return datetime.now()

    def add_order_items(self, order: OrderData) -> None:
        try:
            for sku, (qty, total) in order.items.items():
                self.db.cursor.execute("""
                INSERT INTO oc_order_product (order_id, product_id, name, model, quantity, price, 
                total, tax, reward)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0) 
                """, (order.info['orderid'], self.item_map.get(sku, 0) or 0,
                      self.name_map.get(sku, sku),
                      sku, qty, total / qty, total))
        except DatabaseError as err:
            print(f'Warning adding items for order {order.info["orderid"]}: {err.msg}')
            pass

    def import_order(self, order: CsvRow, comment: str) -> bool:
        print(f'Importing order {order["orderid"]}')

        order_country = self.db.get_country(order['ocountry'])
        order_zone = self.get_zone(order['ostate'], order_country['zone_id']) if order_country else None
        payment_method = order['oauthorization']
        payment_code = 'cod'
        if payment_method.startswith('Approval'):
            payment_method = 'Credit Card / Debit Card (Authorize.Net)'
            payment_code = 'authorizenet_aim'
        shipping_zone = self.get_zone(order['ostate'])
        shipping_method = order['oshipmethod']
        if 'Media Mail' in shipping_method:
            shipping_method = 'Media Mail - 10-20 days'
        elif 'Priority Mail' in shipping_method:
            shipping_method = 'Priority Mail - 3-5 days'
        order_status = self.order_status_map.get(order['order_status'], OrderStatus.COMPLETE)

        try:
            self.db.cursor.execute("""
            INSERT INTO oc_order (order_id, invoice_no, invoice_prefix, store_id, store_name, store_url,
            customer_id, customer_group_id, firstname, lastname, email, telephone, fax, custom_field, 
            payment_firstname, payment_lastname, payment_company, payment_address_1, payment_address_2, 
            payment_city, payment_postcode, payment_country, payment_country_id, payment_zone, 
            payment_zone_id, payment_address_format, payment_custom_field, payment_method, payment_code,
            shipping_firstname, shipping_lastname, shipping_company, shipping_address_1, 
            shipping_address_2, shipping_city, shipping_postcode, shipping_country, shipping_country_id, 
            shipping_zone, shipping_zone_id, shipping_address_format, shipping_custom_field, 
            shipping_method, shipping_code, comment, total, order_status_id, affiliate_id, commission, 
            marketing_id, tracking, language_id, currency_id, currency_code, currency_value, ip, 
            forwarded_ip, user_agent, accept_language, date_added, date_modified)
            VALUES (%s, %s, 'AP', 0, 'The Anonymous Press', 'https://anonpress.org/store/', %s, 1, %s, 
            %s, %s, %s, '', '[]', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '{firstname} {lastname}
    {company}
    {address_1}
    {address_2}
    {city}, {zone} {postcode}
    {country}','[]',%s,%s, %s, %s, %s, %s, %s, %s, %s, 'United States', 223, %s, %s, 
    '{firstname} {lastname}
    {company}
    {address_1}
    {address_2}
    {city}, {zone} {postcode}
    {country}', '[]', %s, '', %s, %s, %s, 0, 0, 0, '', 1, 2, 'USD', 1, '', '', '', '', %s, %s)
            """, (order['orderid'], order['orderid'], order['ocustomerid'], order['ofirstname'],
                  order['olastname'], order['oemail'], order['ophone'],
                  order['ofirstname'], order['olastname'], order['ocompany'],
                  order['oaddress'], order['oaddress2'],
                  order['ocity'], order['ozip'],
                  order_country['name'] if order_country else order['ocountry'],
                  order_country['zone_id'] if order_country else 0,
                  order_zone['name'] if order_zone else order['ostate'],
                  order_zone['zone_id'] if order_zone else 0,
                  payment_method, payment_code, order['oshipfirstname'],
                  order['oshiplastname'], order['oshipcompany'], order['oshipaddress'],
                  order['oshipaddress2'], order['oshipcity'], order['oshipzip'],
                  shipping_zone['name'] if shipping_zone else order['oshipstate'],
                  shipping_zone['zone_id'] if shipping_zone else 0, shipping_method,
                  comment, order['orderamount'], int(order_status),
                  self.parse_date(order['date_started']),
                  self.parse_date(order['last_update'])))
        except DatabaseError as err:
            print(f'Warning importing order {order["orderid"]}: {err.msg}')

        order['imported'] = True
        self.imported_orders += 1
        return True

    def get_zone(self, state: str, country=Database.COUNTRY_ID_US) -> ZoneInfo:
        if country == Database.COUNTRY_ID_US and state in self.zone_info:
            return self.zone_info[state]
        zone_info = self.db.get_code_for_state(state, country)
        if country == Database.COUNTRY_ID_US:
            self.zone_info[state] = zone_info if zone_info is not None else None
        return zone_info

    def import_customer(self, customer: CsvRow) -> bool:
        if args.limit_customers and self.imported_customers >= args.limit_customers:
            return False
        if customer['imported']:
            return True
        print(f'Importing customer {customer["contactid"]}')

        zone = self.get_zone(customer['billing_state'])

        try:
            self.db.cursor.execute("""
            INSERT INTO oc_address (address_id, customer_id, firstname, lastname, company, address_1, address_2, city, postcode, country_id, zone_id, custom_field) VALUES
            (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s, 223, %s, '[]')
            """, (customer['contactid'], customer['billing_firstname'], customer['billing_lastname'],
                  customer['billing_company'], customer['billing_address'],
                  customer['billing_address2'], customer['billing_city'],
                  customer['billing_zip'], zone['zone_id'] if zone else 0))
        except DatabaseError as err:
            print(f'Warning importing address for customer {customer["contactid"]}: {err.msg}')

        address_id = self.db.cursor.lastrowid

        try:
            self.db.cursor.execute("""
            INSERT INTO oc_customer (customer_id, customer_group_id, store_id, language_id, firstname, lastname, email, telephone, fax, password, salt, cart, wishlist, newsletter, address_id, custom_field, ip, status, safe, token, code, date_added) VALUES
            (%s, 1, 0, 1, %s, %s, %s, %s, '', 'reset', 'reset', 'a:0:{}', NULL, %s, %s, '[]', 0, %s, 0, '', '', %s)
            """, (customer['contactid'], customer['billing_firstname'], customer['billing_lastname'],
                  customer['email'], customer['billing_phone'], customer['maillist'],
                  address_id, customer['custenabled'], self.parse_date(customer['last_update'])))
        except DatabaseError as err:
            print(f'Warning importing customer {customer["contactid"]}: {err.msg}')

        customer['imported'] = True
        self.imported_customers += 1
        return True


parser = argparse.ArgumentParser(description='Script to facilitate migration from 3dcart')
parser.add_argument('--customers', help='Customers input file',
                    type=argparse.FileType('r', encoding='latin1'),
                    required=True)
parser.add_argument('--orders', nargs='?', help='Orders input file',
                    type=argparse.FileType('r', encoding='latin1'),
                    required=True)
parser.add_argument('--from-order', nargs='?', type=int, default=0, help='Order number to start')
parser.add_argument('--limit-customers', nargs='?', type=int, help='Limit to number of customers')
parser.add_argument('--limit-orders', nargs='?', type=int, help='Limit to number of orders')

args = parser.parse_args()

migration = Migration(args)
migration.run()

args.customers.close()
args.orders.close()
