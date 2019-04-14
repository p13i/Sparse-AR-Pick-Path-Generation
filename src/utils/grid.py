def are_neighbors_in_grid(coordinate_a, coordinate_b):
    """ Determines if the given cells are neighbors or not. """
    coordinate_a_r, coordinate_a_c = coordinate_a
    coordinate_b_r, coordinate_b_c = coordinate_b

    if abs(coordinate_a_r - coordinate_b_r) == 1 and coordinate_a_c == coordinate_b_c:
        return True

    if coordinate_a_r == coordinate_b_r and abs(coordinate_a_c - coordinate_b_c) == 1:
        return True

    return False
