import numpy
import utm
    
def choose_points(lat, lon, buoy_lat, buoy_lon, flat=False):
    """
    Choose the four closest NARR or MERRA points to a lat/lon position.

    Args:
        lat, lon: numpy arrays, 2d
        buoy_lat, buoy_lon: these is the point to get close to

    Returns:
        chosen indices, coordinates of the 4 closest points (euclidean)
    """

    distances = (lat - buoy_lat)**2 + (lon - buoy_lon)**2
    dist_args_sorted = numpy.argsort(distances.flatten())

    chosen_idxs = dist_args_sorted[0:4]
    chosen_idxs = numpy.unravel_index(chosen_idxs, lat.shape)

    coordinates = list(zip(lat[chosen_idxs], lon[chosen_idxs]))

    return chosen_idxs, coordinates


def is_square_test(points):
    """
    Test if 4 points lie on a grid.

    Args:
        points:
            format = [[x1, y1], [x2, y2], ...]

    Returns:
        true or false, based on result
    """
    p1, p2, p3, p4 = points

    test = int(line_test(p1, p2, p3))
    test += int(line_test(p4, p1, p2))
    test += int(line_test(p3, p4, p1))
    test += int(line_test(p2, p3, p4))

    return test == 0


def line_test(p1, p2, p3, threshold=0.001):
    """
    Check whether the three points lie on a line.
    """
    # http://math.stackexchange.com/questions/441182/how-to-check-if-three-coordinates-form-a-line
    # threshold found with test_line_test.py
    _p1 = numpy.append(p1, 1)
    _p2 = numpy.append(p2, 1)
    _p3 = numpy.append(p3, 1)

    a = numpy.matrix([_p1, _p2, _p3])
    a = numpy.array(a.transpose(), dtype=numpy.float64)

    # TODO check if threshold is still valid
    return abs(numpy.linalg.det(a)) < threshold
