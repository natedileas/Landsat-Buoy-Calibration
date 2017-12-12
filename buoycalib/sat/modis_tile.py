import numpy

from .. import settings

def latlon_to_tile(lat, lon, file_=settings.MODIS_TILE):
	""" convert lat lon pair to containing MODIS tile

	Source: https://earthdatascience.org/tutorials/convert-modis-tile-to-lat-lon/
	"""
	# first seven rows contain header information
	# bottom 3 rows are not data
	data = numpy.loadtxt(file_, skiprows = 7)

	in_tile = False
	i = 0
	while(not in_tile):
	    in_tile = lat >= data[i, 4] and lat <= data[i, 5] and lon >= data[i, 2] and lon <= data[i, 3]
	    i += 1

	vert = data[i-1, 0]
	horiz = data[i-1, 1]
	return vert, horiz

def tile_to_latlon(vert, horiz, file_=settings.MODIS_TILE):
	""" convert MODIS tile to containing lat lon

	return format: lon_min    lon_max   lat_min   lat_max
	"""
	# first seven rows contain header information
	# bottom 3 rows are not data
	data = numpy.loadtxt(file_, skiprows = 7)

	for row in data:
		if row[0] == vert and row[1] == horiz:
			return row[2:]

	raise Exception('Tile: {0} {1} not found.'.format(vert, horiz))

if __name__ == '__main__':
	lat = 40.015
	lon = -105.2705
	print(latlon_to_tile(lat, lon))

	print(tile_to_latlon(4, 9))

