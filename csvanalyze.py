import os, csv, sys
from datetime import datetime, date, timedelta, timezone
from operator import itemgetter

totals = {}
grand_total = 0

def in_carton(v):
	split = v.partition('x')
	if(split[2] == ''):
		return 1
	else:
		return int(split[2])

year_ago = datetime.now(timezone.utc) - timedelta(days=365)
print("Orders since " + year_ago.strftime("%m/%d/%y") + ":")

directory = os.fsencode('uploaded')
for uploaded_file in os.listdir(directory):
	filename = os.fsdecode(uploaded_file)
	uploaded = datetime.strptime(filename, '%Y-%m-%d %H%M%z.csv')
	if(uploaded < year_ago):
		continue
	try:
		with open('uploaded/' + filename, newline='') as f:
			items = [{k: v for k, v in row.items()} for row in csv.DictReader(f, skipinitialspace=True)]
	except UnicodeDecodeError:
		continue
	for row in items:
		try:
			if len(sys.argv) == 2:
				if not (row['itemid'].startswith(sys.argv[1])):
					continue
			if row['itemid'] not in totals:
				totals[row['itemid']] = 0
			totals[row['itemid']] += int(row['numitems'])
			grand_total += int(row['numitems']) * in_carton(row['itemid'])
		except KeyError:
			continue

for k, v in sorted(totals.items(), reverse=True):
	print(k + ": " + str(v) + " (" + "{:.2f}".format(v * in_carton(k) / grand_total * 100) + "%)")
