import buoycalib.sat.modis as modis
from buoycalib import buoy
from datetime import timedelta, date

date_start = date(2010, 5, 1)
date_end = date(2010, 7, 15)
buoy_id = '45012'
b = buoy.all_datasets()[buoy_id]
lat = b.lat
lon = b.lon


def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)

matches = []
for d in daterange(date_start, date_end):
	matches.append(modis.modis_from_landsat(d, lat, lon))

with open('matches.txt', 'w') as f:
	f.write('\n'.join(matches))