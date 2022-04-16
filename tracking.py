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
import ftplib
import re
from typing import NamedTuple

from opencart_db import Database, Items, OrderInfo, OrderStatus


class Shipment(NamedTuple):
    order_id: int
    tracking_number: str
    contents: Items


class Tracking:
    def __init__(self, db_host, db_user, db_pass, db_name, ftp_host, ftp_user, ftp_pass, ftp_path):
        self.db = Database(db_host, db_user, db_pass, db_name)
        self.ftp = ftplib.FTP(ftp_host, ftp_user, ftp_pass)
        self.ftp.cwd(ftp_path)

    tracking_regex = re.compile(r'^\d[A-Z0-9]+ - ((\d+ [^\s]+(, )?)+)$')
    item_regex = re.compile(r'^(\d+) ([^\s]+)$')

    def add_shipment_to_order(self, shipment: Shipment) -> None:
        order = self.db.get_order(shipment.order_id)
        order['comment'] = self.add_shipment_to_comment(order['comment'], shipment)
        if self.is_fully_shipped(order):
            order = self.db.set_order_status(order, OrderStatus.SHIPPED)
        self.db.update_order(order)

    def add_shipment_to_comment(self, comment: str, shipment: Shipment) -> str:
        def items_string(items: Items):
            return ', '.join(f'{qty} {sku}' for sku, qty in items.items())

        return comment + '\n' + f'{shipment.tracking_number} - {items_string(shipment.contents)}'

    def is_fully_shipped(self, order: OrderInfo) -> bool:
        # Parse tracking lines from comment
        shipped_items: Items = {}
        for line in order['comment']:
            try:
                match = self.tracking_regex.search(line)
                contents = match.group(1).split(', ')
                for content in contents:
                    item = self.item_regex.search(content)
                    if item.group(1) not in shipped_items:
                        shipped_items[item.group(1)] = 0
                    shipped_items[item.group(1)] += int(item.group(2))
            except:
                continue
        order_items = self.db.get_order_contents(order['order_id'])
        for order_sku, order_qty in order_items.items():
            if order_sku in ['E', 'e-AA', 'DO', 'DN', 'EPUB', '0', '']:
                # These items do not require shipping.
                # TODO: Could get this from the database
                continue
            if shipped_items[order_sku] < order_qty:
                return False
        return True
