import numpy as np


def angle(a, b):
    """ Computes the angle between two coordinates. """

    # Split for convenience
    a_x, a_y = a
    b_x, b_y = b

    # Compute deltas
    d_y = b_y - a_y
    d_x = b_x - a_x

    # Compute arctan^2 and adjust angle value
    return angle_trunc(np.arctan2(d_y, d_x))


def angle_trunc(angle_rad):
    """ Brings an angle_rad (in radians) to the positive range. """
    while angle_rad < 0.0:
        angle_rad += 2 * np.pi
    return angle_rad


def transform(origin: tuple, coordinates: tuple, theta_rad: float) -> tuple:
    """
    Transforms the given coordinates by theta_rad radians around the given origin.
    I think this is really cool code!
    """

    # Numpy-fy!
    origin = np.array(origin)
    coordinates = np.array(coordinates)

    # Bring coordinates to origin
    coordinates = coordinates - origin

    # Apply transformation matrix
    transformation_matrix = np.array([
        [np.cos(theta_rad), -1 * np.sin(theta_rad)],
        [np.sin(theta_rad), np.cos(theta_rad)]
    ])
    coordinates = np.matmul(transformation_matrix, coordinates)

    # Take coordinates back out from origin
    coordinates = coordinates + origin

    # Provide a tuple back out
    return tuple(coordinates)
