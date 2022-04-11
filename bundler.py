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
from datetime import datetime
from typing import List, Dict

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
        return self.db.get_orders_with_status(OrderStatus.VALIDATED)

    def bundle_order_items(self, items: Items) -> Items:
        bundled = {}
        for sku, qty in items.items():
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
            'FirstName':   order['shipping_firstname'],
            'LastName':    order['shipping_lastname'],
            'Company':     order['shipping_company'],
            'Address1':    order['shipping_address_1'],
            'Address2':    order['shipping_address_2'],
            'City':        order['shipping_city'],
            'State':       order['shipping_state'],
            'Zip':         order['shipping_postcode'].replace('-', ''),
            'Phone':       order['telephone'],
            'Email':       order['email'],
        }

    def __map_ship(self, method: str) -> str:
        for lhs, rhs in self.shipping.items():
            if re.match(lhs, method):
                return rhs
        return method

    FIELDS = ['OrderNumber', 'ShipMethod', 'Comments', 'FirstName', 'LastName', 'Company',
              'Address1', 'Address2', 'City', 'State', 'Zip', 'Phone', 'Email', 'itemid',
              'numitems']

    def write_csv(self, orders: List[OrderInfo]) -> List[OrderInfo]:
        with open(self.filename, 'w', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=self.FIELDS, quoting=csv.QUOTE_NONNUMERIC)
            writer.writeheader()
            for order in orders:
                order_info = self.__map_order(order)
                items = self.bundle_order_items(self.db.get_order_contents(order['order_id']))
                Database.set_order_status(order, OrderStatus.COMPLETE if len(
                    items) == 0 else OrderStatus.PROCESSED)
                for sku, qty in items.items():
                    writer.writerow({**order_info, 'itemid': sku, 'numitems': qty})
            return orders

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
    orders = b.write_csv(b.get_orders())
    b.upload_csv()
    b.update_orders(orders)


if __name__ == "__main__":
    main()
