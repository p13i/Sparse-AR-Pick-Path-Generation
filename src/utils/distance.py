import numpy as np


def _euclidian_distance(a, b):
    """ Straight-line path distance between two coordinates. """
    # Split up coordinates for convenience
    a_x, a_y = a
    b_x, b_y = b

    # Compute the term inside the square root
    radicand = np.float_power(b_x - a_x, 2) + np.float_power(b_y - a_y, 2)

    # Compute distance
    return np.sqrt(radicand)


def minimum_distance(line, point):
    """
    Computes the minimum distance between a line and point.
    Implementation borrowed from Georgia Tech CS Game AI course offering.
    """

    d2 = np.square(_euclidian_distance(*line))

    if d2 == 0.0:
        return _euclidian_distance(point, line[0])

    # Consider the line extending the segment, parameterized as line[0] + t (line[1] - line[0]).
    # We find projection of point p onto the line.
    # It falls where t = [(point-line[0]) . (line[1]-line[0])] / |line[1]-line[0]|^2
    p1 = (point[0] - line[0][0], point[1] - line[0][1])
    p2 = (line[1][0] - line[0][0], line[1][1] - line[0][1])
    t = np.dot(p1, p2) / d2

    if t < 0.0:
        return _euclidian_distance(point, line[0])  # Beyond the line[0] end of the segment
    elif t > 1.0:
        return _euclidian_distance(point, line[1])  # Beyond the line[1] end of the segment

    # projection falls on the segment
    p3 = (line[0][0] + (t * (line[1][0] - line[0][0])), line[0][1] + (t * (line[1][1] - line[0][1])))

    return _euclidian_distance(point, p3)
