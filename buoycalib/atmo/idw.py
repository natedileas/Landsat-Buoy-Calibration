import numpy

def idw(samples, locations, point, power=2):
	""" Shepard's Method (inverse distance weighting interpolation)
	
	Args::
		samples: data to be interpolated, of length n
		locations: locations of the data, shape 2, n
		point: point to interpolate too, shape 2
		power: integer, arbitary

	Returns:
		weighted_samples: samples, weighted by the weights

	Notes::
		from A NOVEL CONFIDENCE METRIC APPROACH FOR A LANDSAT LAND SURFACE
		TEMPERATURE PRODUCT, Monica J. Cook and Dr. John R. Schott
	"""
	distances = numpy.asarray([distance(i, point) for i in locations])
	
	weights = distances ** -power
	weights /= weights.sum()   # normalize to 1

	weighted_samples = [weights[i] * samples[i] for i in range(len(locations))]

	return sum(weighted_samples)


def distance(p1, p2):
	""" Euclidean Distance of 2 iterables """
	x1, y1 = p1
	x2, y2 = p2
	return numpy.sqrt((x1-x2)**2+(y1-y2)**2)


if __name__ == '__main__':
	print(idw([1, 1, 1, 1], [[0, 1], [1, 0], [0, 0], [1, 1]], [0.75, 0.75]))