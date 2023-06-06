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
import csv
import ftplib
import os.path
import re
import unicodedata
from datetime import datetime
from typing import List, Dict, Tuple

from config import Config
from opencart_db import Database, OrderStatus, OrderInfo, Items

CsvRow = Dict[str, str]


class Bundler:
    def __init__(self, db_host, db_user, db_pass, db_name, ftp_host, ftp_user, ftp_pass, ftp_path,
                 bundles, shipping, filename):
        self.db = Database(db_host, db_user, db_pass, db_name)
        self.ftp = ftplib.FTP(ftp_host, ftp_user, ftp_pass)
        self.ftp.cwd(ftp_path)
        self.filename = filename
        self.bundles = bundles
        self.shipping = shipping

    def __del__(self):
        self.ftp.quit()

    def get_orders(self) -> List[OrderInfo]:
        return self.db.get_orders_with_status(OrderStatus.VALIDATED, OrderStatus.VALIDATED_UNPAID)

    def bundle_order_items(self, items: Items) -> Items:
        bundled = {}
        for sku, qty in items.items():
            if sku in Config.ignore:
                continue
            for bundle_qty, bundle_sku in self.bundles.get(sku, {}).items():
                bundles_to_add = qty // bundle_qty
                if bundles_to_add > 0:
                    bundled[bundle_sku] = bundles_to_add
                    qty -= bundle_qty * bundles_to_add
            if qty > 0:
                bundled[sku] = qty
        return bundled

    def __map_order(self, order: OrderInfo) -> CsvRow:
        return {
            'OrderNumber': order['order_id'],
            'ShipMethod':  self.__map_ship(order['shipping_method']),
            'Comments':    '',
            'FirstName':   self.__normalize(order['shipping_firstname']),
            'LastName':    self.__normalize(order['shipping_lastname']),
            'Company':     self.__normalize(order['shipping_company']),
            'Address1':    self.__normalize(order['shipping_address_1']),
            'Address2':    self.__normalize(order['shipping_address_2']),
            'City':        self.__normalize(order['shipping_city']),
            'State':       self.__normalize(order['shipping_state']),
            'Zip':         self.__normalize(order['shipping_postcode']).replace('-', ''),
            'Phone':       self.__normalize(order['telephone']),
            'Email':       self.__normalize(order['email']),
        }

    # WarePak breaks if it receives strings with non-ASCII characters or length > 24. Woo hoo
    def __normalize(self, input: str) -> str:
        return unicodedata.normalize('NFKD', input).encode('ASCII', 'ignore').decode()[:24]

    def __map_ship(self, method: str) -> str:
        for lhs, rhs in self.shipping.items():
            if re.match('.*' + lhs, method):
                return rhs
        if method.startswith('HIDDEN'):
            return method[7:].lstrip('-').lstrip()
        return method

    FIELDS = ['OrderNumber', 'ShipMethod', 'Comments', 'FirstName', 'LastName', 'Company',
              'Address1', 'Address2', 'City', 'State', 'Zip', 'Phone', 'Email', 'itemid',
              'numitems']

    def write_csv(self, orders: List[OrderInfo]) -> Tuple[List[OrderInfo], int]:
        with open(self.filename, 'w', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=self.FIELDS, quoting=csv.QUOTE_ALL,
                                    lineterminator='\n')
            writer.writeheader()
            row_count = 0
            processed_orders: List[OrderInfo] = []
            for order in orders:
                try:
                    order_info = self.__map_order(order)
                    items = self.bundle_order_items(self.db.get_order_contents(order['order_id']))
                    if Database.get_order_status(order) == OrderStatus.VALIDATED:
                        Database.set_order_status(order, OrderStatus.COMPLETE if len(
                            items) == 0 else OrderStatus.PROCESSED)
                    elif Database.get_order_status(order) == OrderStatus.VALIDATED_UNPAID:
                        Database.set_order_status(order, OrderStatus.PROCESSED_UNPAID)
                    for sku, qty in items.items():
                        writer.writerow({**order_info, 'itemid': sku, 'numitems': qty})
                        row_count += 1
                    processed_orders.append(order)
                except Exception as e:
                    print(e)
                    continue
            return processed_orders, row_count

    def update_orders(self, orders: List[OrderInfo]) -> None:
        for order in orders:
            self.db.update_order(order)

    def upload_csv(self) -> None:
        with open(self.filename, 'rb') as file:
            self.ftp.storbinary(f'STOR {os.path.basename(self.filename)}', file)


def main():
    b = Bundler(Config.db_host, Config.db_user, Config.db_pass, Config.db_name,
                Config.ftp_host, Config.ftp_user, Config.ftp_pass, Config.ftp_incoming,
                Config.bundles, Config.shipping,
                filename=datetime.now().strftime('uploaded/%Y-%m-%d_%H%M%z.csv'))
    orders, row_count = b.write_csv(b.get_orders())
    if row_count < 2:
        # Files containing no rows are pointless, and files containing one row don't get
        # processed for reasons we haven't yet been able to fathom.
        return
    b.upload_csv()
    b.update_orders(orders)


if __name__ == "__main__":
    main()
