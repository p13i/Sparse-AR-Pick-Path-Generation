from src.models import NavigationGridCellTypes
import networkx as nx
import itertools
import numpy as np
import logging
from src import utils
import os

logger = logging.getLogger(os.path.basename(__file__))
logger = utils.logging.configure_logger(logger)


def select_unordered_books_for_picking(gt_library_warehouse, num_books):
    return np.random.choice(
        a=gt_library_warehouse.books,
        size=num_books,
        replace=False,
    )


def get_locations_of_books(gt_library_grid_warehouse, target_books):
    """ Gets all the locations of specified books. """
    return [gt_library_grid_warehouse.get_book_location(target_book) for target_book in target_books]


def get_induced_subgraph_on_book_locations(gt_library_grid_warehouse, book_locations):
    """
    Given a list of book locations, this method produces the sub-graph on the navigation grid of these book locations.
    """

    # Ensure the source cell is navigable
    assert gt_library_grid_warehouse.get_cell_type(gt_library_grid_warehouse.source_cell[0],
                                                   gt_library_grid_warehouse.source_cell[1]) == NavigationGridCellTypes.NAVIGABLE_CELL, \
        "Source must be navigable."

    # Ensure all the books are on shelves
    for book_location_r, book_location_c in book_locations:
        assert gt_library_grid_warehouse.get_cell_type(book_location_r,
                                                       book_location_c) == NavigationGridCellTypes.SHELVE_CELL, \
            "Book must be on a shelve."

    G_library = gt_library_grid_warehouse.get_navigation_grid_as_graph()

    G_subgraph = nx.MultiDiGraph()
    G_subgraph.add_node(gt_library_grid_warehouse.source_cell)
    G_subgraph.add_nodes_from(book_locations)

    # Connect each book to each other book
    for location1, location2 in itertools.combinations(G_subgraph.nodes, 2):
        if location1 == gt_library_grid_warehouse.source_cell:
            cell1_location = location1
        else:
            cell1_location = gt_library_grid_warehouse.get_navigable_cell_coordinate_near_book(location1)

        if location2 == gt_library_grid_warehouse.source_cell:
            cell2_location = location2
        else:
            cell2_location = gt_library_grid_warehouse.get_navigable_cell_coordinate_near_book(location2)

        def map_so(x, a, b, c, d):
            """ https://stackoverflow.com/questions/345187/math-mapping-numbers """
            y = (x - a) / (b - a) * (d - c) + c
            return y

        def library_layout(G_library: nx.Graph):
            MIN_ROW = 0
            MAX_ROW = gt_library_grid_warehouse.num_rows - 1

            MIN_COL = 0
            MAX_COL = gt_library_grid_warehouse.num_cols - 1

            position_dict = {}
            for node in G_library.nodes:
                r, c = node
                position_dict[node] = (
                    map_so(r, MIN_ROW, MAX_ROW, -1, 1),
                    map_so(c, MIN_COL, MAX_COL, -1, 1)
                )

            return position_dict

        ### CHECK LAYOUT HERE
        # import matplotlib.pyplot as plt
        # fig, ax = plt.subplots(figsize=(20, 20))
        # pos = library_layout(G_library)
        #
        #
        #
        # nx.draw_networkx_nodes(G_library, pos, ax=ax)
        # nx.draw_networkx_labels(G_library, pos, ax=ax)
        # nx.draw_networkx_edges(G_library, pos, ax=ax)
        # fig.show()
        # fig.savefig('temp.png')

        # Use Dijkstra's algorithm to determine the distance between adjacent shelves
        shortest_path_cost = nx.dijkstra_path_length(G_library, cell1_location, cell2_location)

        G_subgraph.add_edge(location1, location2, weight=shortest_path_cost)
        G_subgraph.add_edge(location2, location1, weight=shortest_path_cost)

    return G_subgraph


def reconstruct_library_graph(gt_library_grid_warehouse, books_and_locations, optimal_pick_path):
    locations_to_books = {gt_library_grid_warehouse.source_cell: []}
    for book, location in books_and_locations:
        if location not in locations_to_books:
            locations_to_books[location] = []
        locations_to_books[location].append(book)

    books = [None]
    new_path = [gt_library_grid_warehouse.source_cell]
    for location in optimal_pick_path:
        # Introduce the location to the new path for how many ever copies of the location are in the path
        for book in locations_to_books[location]:
            books.append(book)
            new_path.append(location)

    books.append(None)
    new_path.append(gt_library_grid_warehouse.source_cell)

    return tuple(books), tuple(new_path)


def get_pick_path_in_library(gt_library_grid_warehouse, optimal_pick_path_locations):
    """ Given the TSP shelve locations, this method returns the actual cell-by-cell pick path in the warehouse. """

    G_library = gt_library_grid_warehouse.get_navigation_grid_as_graph()

    optimal_pick_paths_in_library = []

    # Get the cell-by-cell path between every pair of adjacent nodes in the optimal pick path
    for i in range(len(optimal_pick_path_locations) - 1):
        n1 = optimal_pick_path_locations[i]
        n2 = optimal_pick_path_locations[i + 1]

        if n1 == gt_library_grid_warehouse.source_cell:
            c1 = gt_library_grid_warehouse.source_cell
        else:
            c1 = gt_library_grid_warehouse.get_navigable_cell_coordinate_near_book(n1)

        if n2 == gt_library_grid_warehouse.source_cell:
            c2 = gt_library_grid_warehouse.source_cell
        else:
            c2 = gt_library_grid_warehouse.get_navigable_cell_coordinate_near_book(n2)

        # Use dijkstra's algorithm to get the best path in the library
        path = nx.dijkstra_path(G_library, c1, c2)

        if n1 != gt_library_grid_warehouse.source_cell:
            path = [n1] + path

        if n2 != gt_library_grid_warehouse.source_cell:
            path = path + [n2]

        optimal_pick_paths_in_library.append(path)

    for i in range(len(optimal_pick_paths_in_library)):
        optimal_pick_paths_in_library[i] = shortcut_paths(gt_library_grid_warehouse, optimal_pick_paths_in_library[i])

    return optimal_pick_paths_in_library


def shortcut_paths(gt_library_warehouse, cell_by_cell_book_to_book_path):
    logger.debug('Shortcutting path with %d cells.' % len(cell_by_cell_book_to_book_path))

    shortcut_path = []

    # Remove the 0th and last cells from consideration
    # because we want to keep those no matter what
    cell_by_cell_navigable_path = cell_by_cell_book_to_book_path[1:-1]

    i = 0
    while i < len(cell_by_cell_navigable_path):

        j = i
        farthest_clear_shot_index = j

        while j < len(cell_by_cell_navigable_path):

            current_cell = cell_by_cell_navigable_path[i]
            proposed_shortcut_cell = cell_by_cell_navigable_path[j]

            if gt_library_warehouse.is_clear_shot(current_cell, proposed_shortcut_cell):
                # Keep looking forward
                farthest_clear_shot_index = j

            j += 1

        shortcut_path.append(cell_by_cell_navigable_path[farthest_clear_shot_index])

        i = farthest_clear_shot_index + 1

    shortcut_path = cell_by_cell_book_to_book_path[:2] + shortcut_path + cell_by_cell_book_to_book_path[-1:]

    logger.debug('Path now has %d cells.' % len(shortcut_path))

    return shortcut_path

def get_pick_path_as_dict(path_id, path_type,
                          unordered_books, unordered_books_locations,
                          ordered_books, ordered_locations_optimal,
                          optimal_pick_path_in_library):
    unordered_books_and_locations = [{'book': book.as_dict(), 'location': location} for book, location in
                                     zip(unordered_books, unordered_books_locations)]
    ordered_books_and_locations = [{'book': book.as_dict(), 'location': location} for book, location in
                                   zip(ordered_books[1:-1], ordered_locations_optimal[1:-1])]

    ordered_pick_path = []
    for j in range(len(optimal_pick_path_in_library)):

        if j == len(optimal_pick_path_in_library) - 1:
            target_book, target_location = None, None
        else:
            target_book, target_location = ordered_books[j + 1].as_dict(), ordered_locations_optimal[j + 1]

        ordered_pick_path.append({
            'stepNumber': j + 1,
            'cellByCellPathToTargetBookLocation': optimal_pick_path_in_library[j],
            'targetBookAndTargetBookLocation': {
                'book': target_book,
                'location': target_location
            },
        })

    return {
        'pathId': path_id,
        'pathType': path_type,
        'pickPathInformation': {
            'unorderedBooksAndLocations': unordered_books_and_locations,
            'orderedBooksAndLocations': ordered_books_and_locations,
            'orderedPickPath': ordered_pick_path,
        }
    }

