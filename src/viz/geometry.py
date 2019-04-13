import numpy as np
from src.utils import distance
from src.utils.numpy_decorators import return_list_of_tuples, return_tuple


def centroid(polygon):
    x_points = [point[0] for point in polygon]
    y_points = [point[1] for point in polygon]
    c = (np.average(x_points), np.average(y_points))
    return np.asarray(c, dtype=np.int_)


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


@return_tuple
def calculate_point_on_path(path, ratio_onto_path: float = None, distance_onto_path: float = None):

    if ratio_onto_path is None:
        assert distance_onto_path is not None
    elif distance_onto_path is None:
        assert ratio_onto_path is not None
    else:
        assert ratio_onto_path is not None and distance_onto_path is not None

    path_start = np.asarray(path[0], dtype=np.int_)
    path_end = np.asarray(path[1], dtype=np.int_)

    if np.array_equal(path_start, path_end):
        return np.array(path_start)

    v = (path_end - path_start)
    unit_vector = v / np.linalg.norm(v, ord=2)

    # If only the ratio is defined, then compute the real distance
    if ratio_onto_path is not None:
        path_length = distance._euclidian_distance(*path)
        unit_vector_multiplier = path_length * ratio_onto_path
    else:
        unit_vector_multiplier = distance_onto_path

    point = path_start + unit_vector * unit_vector_multiplier

    if any(np.isnan(v) for v in point):
        a = 42

    return point
