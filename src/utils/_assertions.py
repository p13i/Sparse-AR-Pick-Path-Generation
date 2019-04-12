from ._distance import _euclidian_distance

def assert_library_pick_path_is_proper(optimal_pick_path_in_library, optimal_pick_path, source):
    # Ensure the start and end positions are proper
    for i, pick_path in enumerate(optimal_pick_path_in_library):
        expected_path_beginning = source if i == 0 else optimal_pick_path[i]
        expected_path_ending = source if i == len(optimal_pick_path_in_library) - 1 else optimal_pick_path[i + 1]

        assert pick_path[0] == expected_path_beginning
        assert pick_path[-1] == expected_path_ending

    # Ensure every step is one cell away
    # for pick_path in optimal_pick_path_in_library:
    #     for i in range(len(pick_path) - 1):
    #         curr_x, curr_y = pick_path[i]
    #         next_x, next_y = pick_path[i + 1]
    #
    #         assert abs(curr_x - next_x) + abs(curr_y - next_y) == 1


def assert_library_pick_path_has_cost(optimal_library_pick_path, expected_cost, number_of_books):
    actual_cost = 0
    # Ensure every step is one cell away
    for pick_path in optimal_library_pick_path:
        for i in range(len(pick_path) - 1):
            curr_x, curr_y = pick_path[i]
            next_x, next_y = pick_path[i + 1]

            actual_cost += _euclidian_distance((curr_x, curr_y), (next_x, next_y))

    # Every book adds two extra steps (move to book cell, move away from book cell)
    actual_cost -= number_of_books * 2

    assert actual_cost <= expected_cost
