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
from typing import NamedTuple

from opencart_db import Database, Items, OrderInfo


class Shipment(NamedTuple):
    order_id: int
    tracking_number: str
    contents: Items


class Tracking:
    def __init__(self, db_host, db_user, db_pass, db_name, ftp_host, ftp_user, ftp_pass, ftp_path):
        self.db = Database(db_host, db_user, db_pass, db_name)
        self.ftp = ftplib.FTP(ftp_host, ftp_user, ftp_pass)
        self.ftp.cwd(ftp_path)

    def add_shipment_to_order(self, shipment: Shipment) -> None:
        order = self.db.get_order(shipment.order_id)
        order['comment'] = self.add_shipment_to_comment(order['comment'], shipment)
        self.db.update_order(order)

    def add_shipment_to_comment(self, comment: str, shipment: Shipment) -> str:
        # TODO
        return comment

    def is_fully_shipped(self, order: OrderInfo, shipment: Shipment) -> bool:
        # TODO
        return True
