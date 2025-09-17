# Copyright 2018 The Anonymous Press, Inc.
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
import os
import sys
from datetime import datetime, timedelta, timezone

totals = {}
grand_total = 0


def in_carton(v):
    split = v.partition('x')
    if split[2] == '':
        return 1
    else:
        return int(split[2])


# start_date = datetime.strptime('2020-10-12 0000-0500', '%Y-%m-%d %H%M%z')
# end_date = datetime.strptime('2021-10-12 2359-0500', '%Y-%m-%d %H%M%z')

start_date = datetime.now(timezone.utc) - timedelta(days=366)
end_date = datetime.now(timezone.utc) - timedelta(days=1)
print("Orders between " + start_date.strftime("%m/%d/%y") + " and " + end_date.strftime("%m/%d/%y"))

directory = os.fsencode('uploaded')
for uploaded_file in os.listdir(directory):
    filename = os.fsdecode(uploaded_file)
    uploaded = datetime.strptime(filename, '%Y-%m-%d %H%M%z.csv')
    if not (start_date <= uploaded <= end_date):
        continue
    try:
        with open('uploaded/' + filename, newline='') as f:
            items = [{k: v for k, v in row.items()} for row in
                     csv.DictReader(f, skipinitialspace=True)]
    except UnicodeDecodeError:
        continue
    for row in items:
        try:
            if len(sys.argv) == 2 and not (row['itemid'].startswith(sys.argv[1])):
                continue
            if row['itemid'] not in totals:
                totals[row['itemid']] = 0
            totals[row['itemid']] += int(row['numitems'])
            grand_total += int(row['numitems']) * in_carton(row['itemid'])
        except KeyError:
            continue

for k, v in sorted(totals.items(), reverse=True):
    print(k + ": " + str(v) + " (" + "{:.2f}".format(v * in_carton(k) / grand_total * 100) + "%)")
