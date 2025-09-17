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

class Config:
    usps_user = '000AAAAA0000'
    db_host = 'mysql.example.com'
    db_user = 'store'
    db_pass = 'passw0rd'
    db_name = 'store'
    ftp_host = 'ftp.example.com'
    ftp_user = 'whoever'
    ftp_pass = 'passw0rd'
    ftp_incoming = 'incoming/'
    ftp_outgoing = 'outgoing/'

    # SKUs to bundle, and bundle quantities.
    # Keep the right hand side sorted by descending number of books.
    # The bundle quantities should be a canonical system:
    # https://en.wikipedia.org/wiki/Change-making_problem#Greedy_method
    bundles = {
        'MI': {100: 'MIx100', 10: 'MIx10'},
    }

    # SKUs to remove from the output files.
    # Orders containing only these SKUs will be marked as "complete" without being shipped.
    ignore = ['e-AA']

    # Values containing matches for the regular expressions on the left will be replaced with
    # the strings on the right. Others will be passed through.
    shipping = {
        'Priority': 'Priority Mail',
        'Media': 'Media Mail',
    }
