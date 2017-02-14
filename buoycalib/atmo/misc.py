import numpy

def integrate(x, y, method='trap'):
    """
    Approximate integration given two arrays.
    
    Args:
        x, y: points to approximate 1d intergation with.
        method: trapezoidal or rectangular integration. in most cases, it does not matter.

    Returns:
        total: "integral" of arrays.
    """
    total = 0
    
    if method == 'trap':
        for i in xrange(len(x)):
            try:
                # calculate area of trapezoid and add to total
                area = .5*(x[i+1]-x[i])*(y[i]+y[i+1])
                total += area
            except IndexError:
                break
                
    if method == 'rect':
        for i in xrange(0, len(x)):
            try:
                # calculate area of rectangle and add to total
                area = (x[i+1]-x[i])*(y[i])
                total += abs(area)
            except IndexError:
                break
                
    return total

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

    return (test == 0)
    
def line_test(p1, p2, p3):
    """
    Check whether the three points lie on a line.
    """
    # http://math.stackexchange.com/questions/441182/how-to-check-if-three-coordinates-form-a-line
    # threshold found with test_line_test.py
    _p1 = numpy.append(p1, 1)
    _p2 = numpy.append(p2, 1)
    _p3 = numpy.append(p3, 1)

    a = numpy.matrix([_p1, _p2, _p3])
    a = a.transpose()

    return (abs(numpy.linalg.det(a)) < 0.001)   # TODO check if threshold is still valid

