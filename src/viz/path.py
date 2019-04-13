import numpy as np
from . import geometry
from src.utils.numpy_decorators import return_list_of_tuples, return_tuple


@return_list_of_tuples
def adjust_path(path, by_px: int, direction='right'):
    assert direction == 'right', 'Only right is support right now.'

    # 90 degrees to the right
    start_adjustment_angle_rad = np.pi / 2.0
    end_adjustment_angle_rad = -1 * start_adjustment_angle_rad

    path_start, path_end = path

    # Move the point forward by the given distance along the line
    new_path_start = geometry.calculate_point_on_path([path_start, path_end], distance_onto_path=by_px)

    # Rotate about the original point by the adjustment angle
    new_path_start = geometry.transform(path_start, new_path_start, start_adjustment_angle_rad)

    # Move the point forward by the given distance along the line
    new_path_end = geometry.calculate_point_on_path([path_end, path_start], distance_onto_path=by_px)

    # Rotate about the original point by the adjustment angle
    new_path_end = geometry.transform(path_end, new_path_end, end_adjustment_angle_rad)

    if any(np.isnan(v) for arr in [new_path_start, new_path_end] for v in arr):
        a = 42

    return new_path_start, new_path_end


@return_list_of_tuples
def extend_path(path, by_px: int):
    pass