import numpy


def linear(x0, x1, y0, y1, x):
	""" Linear Interpolation
	Source: https://en.wikipedia.org/wiki/Linear_interpolation

	Args: 
		x0, x1: x values to interpolate from
		y0, y1: data, or y values to interpolate from
		x: x value to interpolate to
	"""
	y = y0 + (x - x0) * ((y1 - y0) / (x1 - x0))
	return y


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


def interp_time(date, a1, a2, t1, t2):
    """ linear interp.
    Args:
        date: Python datetime object
        a1, a2: 2 numpy arrays, same dimensions as each other and output
    """
    hour = date.hour
    minute = date.minute
    second = date.second

    # round to nearest minute
    if second > 30: minute = minute + 1

    # convert hour-min acquisition time to decimal time
    time = hour + minute / 60.0

    # interpolate in time
    a = a1 + (time - t1.hour) * ((a2 - a1)/(t2.hour - t1.hour))

    return a


def offset_interp_space(buoy_coor, atmo_profiles, narr_coor):
    """
    Interpolate in space between the 4 profiles with an offset algorithm.

    Args:
        buoy_coor: coordinates to interpolate to
        atmo_profiles: data to interpolate
        narr_coor: coordinates to interpolate from

    Returns:
        the interpolated profile
    """
    atmo_profiles = numpy.array(atmo_profiles)
    length = numpy.shape(atmo_profiles)[2]
    atmo_profiles = numpy.array(atmo_profiles[:, :length])
    narr_coor = numpy.asarray(narr_coor, dtype=float).round(8)

    alpha, beta = calc_interp_weights(narr_coor, buoy_coor)

    if abs(alpha) > 100 or abs(beta) > 100:
        alpha, beta = calc_interp_weights(numpy.absolute(narr_coor), numpy.absolute(buoy_coor))

    height = use_interp_weights(atmo_profiles[:, 0], alpha, beta)
    press = use_interp_weights(atmo_profiles[:, 1], alpha, beta)
    temp = use_interp_weights(atmo_profiles[:, 2], alpha, beta)
    relhum = use_interp_weights(atmo_profiles[:, 3], alpha, beta)

    return height, press, temp, relhum


def calc_interp_weights(interp_from, interp_to):
    """
    Calculate weights for the offset bilinear interpolation  of 4 points.

    Args:
        interp_from: coordinates to interpolate from
        interp_to: coordinates to interpolate to

    Returns:
        alpha, beta: weights to use with use_interp_weights()

    Notes:
        this function is intended to be paired with use_interp_weights().
        Source:
    """
    a = -interp_from[0,0] + interp_from[2,0]
    b = -interp_from[0,0] + interp_from[1,0]
    c = interp_from[0,0] - interp_from[1,0] - interp_from[2,0] + interp_from[3,0]
    d = interp_to[0] - interp_from[0,0]

    e = -interp_from[0,1] + interp_from[2,1]
    f = -interp_from[0,1] + interp_from[1,1]
    g = interp_from[0,1] - interp_from[1,1] - interp_from[2,1] + interp_from[3,1]
    h = interp_to[1] - interp_from[0,1]

    i = math.sqrt(abs(-4*(c*e - a*g)*(d*f - b*h) + (b*e - a*f + d*g - c*h)**2))

    alpha = -(b*e - a*f + d*g - c*h + i)/(2*c*e - 2*a*g)
    beta  = -(b*e - a*f - d*g + c*h + i)/(2*c*f - 2*b*g)

    return alpha, beta


def use_interp_weights(array, alpha, beta):
    """ Calculate the offset bilinear interpolation  of 4 points. """
    return ((1 - alpha) * ((1 - beta) * array[0] + beta * array[1]) + \
            alpha * ((1 - beta) * array[2] + beta * array[3]))


def bilinear_interp_space(buoy_coor, atmo_profiles, data_coor):
    """
    Interpolate in space between the 4 profiles.

    Args:
        buoy_coor: coordinates to interpolate to
        atmo_profiles: data to interpolate
        data_coor: coordinates to interpolate from

    Returns:
        the interpolated profile
    """
    # shape of atmo profiles - 4 x 4 x X
    #                     points x data type x layers
    atmo_profiles = numpy.array(atmo_profiles)
    length = numpy.shape(atmo_profiles)[2]
    atmo_profiles = numpy.array(atmo_profiles[:,:length])
    data_coor = list(data_coor)

    height_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,0,:]) for i in range(4)]
    height = bilinear_interpolation(buoy_coor[0], buoy_coor[1], height_points)

    press_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,1,:]) for i in range(4)]
    press = bilinear_interpolation(buoy_coor[0], buoy_coor[1], press_points)

    temp_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,2,:]) for i in range(4)]
    temp = bilinear_interpolation(buoy_coor[0], buoy_coor[1], temp_points)

    relhum_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,3,:]) for i in range(4)]
    relhum = bilinear_interpolation(buoy_coor[0], buoy_coor[1], relhum_points)

    return [height, press, temp, relhum]


def bilinear_interpolation(x, y, points):
    """Interpolate (x,y) from values associated with four points.

    Args:
        x, y: point to interpolate to
        points: The four points are a list of four triplets:  (x, y, value).
        The four points can be in any order.  They should form a rectangle.

    Returns:
        Interpolated stuff.

    Raises:
        ValueError: if points are not the right type/values to use this function

    Notes:
        See formula at:  http://en.wikipedia.org/wiki/Bilinear_interpolation
    """

    points = sorted(points)               # order points by x, then by y
    (x1, y1, q11), (_x1, y2, q12), (x2, _y1, q21), (_x2, _y2, q22) = points

    if x1 != _x1 or x2 != _x2 or y1 != _y1 or y2 != _y2:
        raise ValueError('points do not form a rectangle')
    if not x1 <= x <= x2 or not y1 <= y <= y2:
        raise ValueError('(x, y) not within the rectangle')

    return (q11 * (x2 - x) * (y2 - y) +
            q21 * (x - x1) * (y2 - y) +
            q12 * (x2 - x) * (y - y1) +
            q22 * (x - x1) * (y - y1)
           ) / ((x2 - x1) * (y2 - y1) + 0.0)



if __name__ == '__main__':
	print(idw([1, 1, 1, 1], [[0, 1], [1, 0], [0, 0], [1, 1]], [0.75, 0.75]))
	print(idw([1, 1, 1, 1], [[0, 1], [1, 0], [0, 0], [1, 1]], [0.75, 0.75]))