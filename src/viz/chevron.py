import numpy as np
from . import geometry
from src.utils import distance
from src.utils.numpy_decorators import return_list_of_tuples, return_tuple


def get_chevron_angle_transform_for_coordinates(a, b):
    """ Gets the angle transformation from vertical of the chevron (arrow) between the two coordinates. """
    return geometry.angle(a, b) + (np.pi / np.float_(2))


@return_list_of_tuples
def get_transformed_chevron(origin, transform_angle, square_side_length):
    """ Creates coordinates for a triangle in the given direction centered at the given origin. """

    # Split for convenience
    (o_x, o_y) = origin

    # This is how many pixels each coordinate will be offset in the x or y direction
    chevron_offset_px = square_side_length / 4

    # Compute the upwards direction arrow
    (a_x, a_y) = (o_x - chevron_offset_px, o_y + chevron_offset_px)
    (b_x, b_y) = (o_x + chevron_offset_px, o_y + chevron_offset_px)
    (c_x, c_y) = (o_x, o_y - chevron_offset_px)

    # Pack up the angles
    (a, b, c) = (a_x, a_y), (b_x, b_y), (c_x, c_y)

    # Apply angle transformation
    a = geometry.transform(origin, a, transform_angle)
    b = geometry.transform(origin, b, transform_angle)
    c = geometry.transform(origin, c, transform_angle)

    return np.array((a, b, c))


@return_list_of_tuples
def translate_polygon_to(polygon, to_centroid):
    polygon_centroid = geometry.centroid(polygon)

    translation_vector = to_centroid - polygon_centroid

    return polygon + translation_vector
