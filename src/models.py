import itertools
import numpy as np
from src import utils
import logging
import os
import json
import networkx as nx
from numpy import uint8 as _DEFAULT_INT_DTYPE
from typing import Tuple

logger = logging.getLogger(os.path.basename(__file__))
logger = utils.logging.configure_logger(logger)

WAREHOUSE_JSON_FILE_FORMAT_VERSION = '2.0'


class NavigationGridCellTypes(object):
    NAVIGABLE_CELL = _DEFAULT_INT_DTYPE(0)
    OBSTACLE_CELL = _DEFAULT_INT_DTYPE(1)
    SHELVE_CELL = _DEFAULT_INT_DTYPE(2)
    NP_DTYPE = _DEFAULT_INT_DTYPE


Coordinate = Tuple[int, int]


class Book(object):
    def __init__(self, title, author, aisle, column, row):
        self.title = title
        self.author = author
        self.aisle = aisle
        self.column = column
        self.row = row

    @property
    def tag(self):
        return f'{self.aisle}-{self.column}-{self.row}'

    @property
    def column_tag(self):
        return f'{self.aisle}-{self.column}'

    def __str__(self):
        return f'{self.tag}: {self.title} by {self.author}'

    def __hash__(self):
        """ Hacky, but it works! """
        return hash(str(self))

    def __eq__(self, other):
        """ Hacky, but it works! """
        return str(self) == str(other)

    def as_dict(self):
        return {
            "title": self.title,
            "author": self.author,
            "tag": self.tag,
        }


class GTLibraryGridWarehouse(object):
    def __init__(self,
                 source_cell,
                 dimensions,
                 total_num_columns_in_grid,
                 navigation_grid,
                 column_tags_to_navigation_grid_coordinates,
                 book_dicts):
        """ TODO: Clean up this method """
        self.source_cell = source_cell

        self.dimensions = dimensions

        # THe number of columns in the grid. Each column houses 5 shelves. Each shelve houses one book.
        self.total_num_columns_in_grid = total_num_columns_in_grid

        # Make sure the dimensions provided match those actually of the navigation grid
        self.navigation_grid = np.array(navigation_grid, dtype=NavigationGridCellTypes.NP_DTYPE)
        assert self.navigation_grid.shape == self.dimensions, f'{self.navigation_grid.shape} != {self.dimensions}'

        for row in navigation_grid:
            for cell in row:
                assert cell in (NavigationGridCellTypes.NAVIGABLE_CELL,
                                NavigationGridCellTypes.OBSTACLE_CELL,
                                NavigationGridCellTypes.SHELVE_CELL), \
                    f'Cell {cell} is unknown.'

        assert len(column_tags_to_navigation_grid_coordinates) == self.total_num_columns_in_grid

        # Below is a reverse mapping of column_tags_to_navigation_grid_coordinates
        self.navigation_grid_coordinates_to_columns_tags = {
            tuple(location): tag
            for tag, location in
            column_tags_to_navigation_grid_coordinates.items()}

        self.books = []
        for book_dict in book_dicts:
            self.books.append(Book(
                # Book information
                title=book_dict['book']['title'],
                author=book_dict['book']['author'],

                # Location information
                aisle=book_dict['location']['aisle'],
                column=book_dict['location']['column'],
                row=book_dict['location']['row'],
            ))

    @property
    def num_rows(self):
        return self.dimensions[0]

    @property
    def num_cols(self):
        return self.dimensions[1]

    def get_book_location(self, target_book):
        """ Given a Book instance, finds the (r, c) location of the book in this warehouse. """

        for r in range(self.num_rows):
            for c in range(self.num_cols):
                cell: NavigationGridCellTypes.NP_DTYPE = self.get_cell_type(r, c)

                # Only examine shelve cells that contain the books
                if cell != NavigationGridCellTypes.SHELVE_CELL:
                    continue

                column_tag_at_location = self.get_column_tag_from_row_and_col(r, c)

                if column_tag_at_location == target_book.column_tag:
                    return (r, c)

        raise ValueError(f'Couldn\'t find book: {target_book}')

    def get_locations_of_books(self, target_books):
        """ Gets all the locations of specified books. """
        return [self.get_book_location(target_book) for target_book in target_books]

    def get_cell_type(self, row, col):
        """ Returns the type of the cell type at the given row and column. """
        return self.navigation_grid[row][col]

    def get_column_tag_from_row_and_col(self, row, col):
        """ Gets the column tag for the cell at the given row and column. """
        return self.navigation_grid_coordinates_to_columns_tags.get((row, col))

    def get_aisle_tag_from_column_tag(self, column_tag):
        """ Gets the aisle tag associated with the provided column tag. """
        return column_tag[0]

    def is_clear_shot(self, coordinate_a, coordinate_b, radius=0.875) -> bool:
        """
        Determines if there is an unobstructed path from coordinate A to coordinate B. 'Unobstructed' is defined as a
        path with no collisions with non-NAVIGABLE_CELL cells. If the radius is provided, it ensures that the clear
        shot computation is buffered on both sides of the search beam by two additional beams each one radius unit
        parallel to the central search beam.
        """

        assert radius > 0.0

        permissible_coordinate_cell_types = (
            NavigationGridCellTypes.NAVIGABLE_CELL,
            NavigationGridCellTypes.SHELVE_CELL,
        )
        assert self.get_cell_type(*coordinate_a) in permissible_coordinate_cell_types
        assert self.get_cell_type(*coordinate_b) in permissible_coordinate_cell_types

        if coordinate_a == coordinate_b:
            return True

        # Defines a line starting from A going to B
        central_search_beam_path = coordinate_a, coordinate_b

        # Defines the offset row and column values to consider when searching for a collision with the central beam
        # Evaluates to: [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)]
        cell_border_offsets = list(itertools.product((-1, 0, +1), repeat=2))

        for r in range(self.num_rows):
            for c in range(self.num_cols):
                for offset_r, offset_c in cell_border_offsets:

                    # Simply add the new offsets to determine where we're searching in this iteration of the loop
                    new_r, new_c = r + offset_r, c + offset_c

                    # If the offset takes out of the bounds of the grid, then ignore
                    if new_r < 0 or new_r >= self.num_rows or new_c < 0 or new_c >= self.num_cols:
                        continue

                    # If the distance between central search beam and offset coordinates are less than the radius...
                    if utils.distance.minimum_distance(central_search_beam_path, (new_r, new_c)) <= radius:
                        # And the offset coordinates are not navigable, then...
                        if self.get_cell_type(new_r, new_c) is not NavigationGridCellTypes.NAVIGABLE_CELL:
                            # Indicate that this particular search beam is not a clear shot
                            return False

        # All checks passed, this is a clear shot
        return True

    @classmethod
    def from_file(cls, warehouse_file_path):
        """ Loads the given JSON file and returns a GTLibraryGridWarehouse instance. """

        with open(warehouse_file_path) as f:
            warehouse_data = json.load(f)

        assert warehouse_data['version'] == WAREHOUSE_JSON_FILE_FORMAT_VERSION

        layout = warehouse_data['warehouseLayout']

        return GTLibraryGridWarehouse(
            source_cell=tuple(layout['sourceCell']),
            dimensions=(layout['numRows'], layout['numCols']),
            navigation_grid=layout['navigationGrid'],
            total_num_columns_in_grid=layout['totalNumColumnsInGrid'],
            column_tags_to_navigation_grid_coordinates=layout['columnTagsToNavigationGridCoordinates'],
            book_dicts=warehouse_data['books'],
        )

    def navigation_grid_as_graph(self, unit_cost=1):
        """ Converts navigation grid into a graph where neighboring cells are connected. """

        G = nx.MultiDiGraph()

        # Add all navigable cells to the warehouse library grid
        for r in range(self.num_rows):
            for c in range(self.num_cols):
                # Skip navigable cells like book locations or obstacles
                if self.get_cell_type(r, c) != NavigationGridCellTypes.NAVIGABLE_CELL:
                    continue

                # Only add navigable cells
                G.add_node((r, c))

        # For each pair of navigable cells in the
        for n1, n2 in itertools.combinations(G.nodes, 2):
            if self.are_neighbors_in_grid(n1, n2):
                G.add_edge(n1, n2, weight=unit_cost)
                G.add_edge(n2, n1, weight=unit_cost)

        return G

    def are_neighbors_in_grid(self, coordinate_a, coordinate_b):
        """ Determines if the given cells are neighbors or not. """
        coordinate_a_r, coordinate_a_c = coordinate_a
        coordinate_b_r, coordinate_b_c = coordinate_b

        if abs(coordinate_a_r - coordinate_b_r) == 1 and coordinate_a_c == coordinate_b_c:
            return True

        if coordinate_a_r == coordinate_b_r and abs(coordinate_a_c - coordinate_b_c) == 1:
            return True

        return False

    def get_navigable_cell_coordinate_near_book(self, book_coordinate):
        """ Returns the navigable cell closest to the given book coordinate. """
        book_coordinate_r, book_coordinate_c = book_coordinate

        # Use the book's shelve aisle to determine where the nearest navigable cell is
        column_tag = self.get_column_tag_from_row_and_col(book_coordinate_r, book_coordinate_c)
        aisle_tag = self.get_aisle_tag_from_column_tag(column_tag)

        if aisle_tag in ('A', 'C', 'E', 'G'):
            # Then, look to the cell below
            return (book_coordinate_r + 1, book_coordinate_c)

        elif aisle_tag in ('B', 'D', 'F'):
            # Then, book to the cell above
            return (book_coordinate_r - 1, book_coordinate_c)

    def get_subgraph_on_book_locations(self, book_locations):
        """
        Given a list of book locations, this method produces the sub-graph on the navigation grid of these book locations.
        """

        # Ensure the source cell is navigable
        assert self.get_cell_type(self.source_cell[0],
                                  self.source_cell[1]) == NavigationGridCellTypes.NAVIGABLE_CELL, \
            "Source must be navigable."

        # Ensure all the books are on shelves
        for book_location_r, book_location_c in book_locations:
            assert self.get_cell_type(book_location_r,
                                      book_location_c) == NavigationGridCellTypes.SHELVE_CELL, \
                "Book must be on a shelve."

        G_library = self.navigation_grid_as_graph()

        G_subgraph = nx.MultiDiGraph()
        G_subgraph.add_node(self.source_cell)
        G_subgraph.add_nodes_from(book_locations)

        # Connect each book to each other book
        for location1, location2 in itertools.combinations(G_subgraph.nodes, 2):
            if location1 == self.source_cell:
                cell1_location = location1
            else:
                cell1_location = self.get_navigable_cell_coordinate_near_book(location1)

            if location2 == self.source_cell:
                cell2_location = location2
            else:
                cell2_location = self.get_navigable_cell_coordinate_near_book(location2)

            def map_so(x, a, b, c, d):
                """ https://stackoverflow.com/questions/345187/math-mapping-numbers """
                y = (x - a) / (b - a) * (d - c) + c
                return y

            def library_layout(G_library: nx.Graph):
                MIN_ROW = 0
                MAX_ROW = 24

                MIN_COL = 0
                MAX_COL = 11

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
            # fig = plt.figure(figsize=(20, 20))
            # pos = library_layout(G_library)
            #
            #
            #
            # nx.draw_networkx_nodes(G_library, pos)
            # nx.draw_networkx_labels(G_library, pos)
            # nx.draw_networkx_edges(G_library, pos)
            # plt.show()

            # Use Dijkstra's algorithm to determine the distance between adjacent shelves
            shortest_path_cost = nx.dijkstra_path_length(G_library, cell1_location, cell2_location)

            G_subgraph.add_edge(location1, location2, weight=shortest_path_cost)
            G_subgraph.add_edge(location2, location1, weight=shortest_path_cost)

        return G_subgraph

    def get_pick_path_in_library(self, optimal_pick_path_locations):
        """ Given the TSP shelve locations, this method returns the actual cell-by-cell pick path in the warehouse. """

        G_library = self.navigation_grid_as_graph()

        optimal_pick_paths_in_library = []

        # Get the cell-by-cell path between every pair of adjacent nodes in the optimal pick path
        for i in range(len(optimal_pick_path_locations) - 1):
            n1 = optimal_pick_path_locations[i]
            n2 = optimal_pick_path_locations[i + 1]

            if n1 == self.source_cell:
                c1 = self.source_cell
            else:
                c1 = self.get_navigable_cell_coordinate_near_book(n1)

            if n2 == self.source_cell:
                c2 = self.source_cell
            else:
                c2 = self.get_navigable_cell_coordinate_near_book(n2)

            # Use dijkstra's algorithm to get the best path in the library
            path = nx.dijkstra_path(G_library, c1, c2)

            if n1 != self.source_cell:
                path = [n1] + path

            if n2 != self.source_cell:
                path = path + [n2]

            optimal_pick_paths_in_library.append(path)

        for i in range(len(optimal_pick_paths_in_library)):
            optimal_pick_paths_in_library[i] = self.shortcut_paths(optimal_pick_paths_in_library[i])

        return optimal_pick_paths_in_library

    def shortcut_paths(self, cell_by_cell_book_to_book_path):
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

                if self.is_clear_shot(current_cell, proposed_shortcut_cell):
                    # Keep looking forward
                    farthest_clear_shot_index = j
                # else:
                #     # The clear shot has ended, so set the variable one back and shortcut the path
                #     farthest_clear_shot_index -= 1
                #     break

                j += 1

            shortcut_path.append(cell_by_cell_navigable_path[farthest_clear_shot_index])

            i = farthest_clear_shot_index + 1

        shortcut_path = cell_by_cell_book_to_book_path[:1] + shortcut_path + cell_by_cell_book_to_book_path[-1:]

        logger.debug('Path now has %d cells.' % len(shortcut_path))

        return shortcut_path

    def reintroduce_duplicate_column_locations(self, books_and_locations, optimal_pick_path):
        locations_to_books = {self.source_cell: []}
        for book, location in books_and_locations:
            if location not in locations_to_books:
                locations_to_books[location] = []
            locations_to_books[location].append(book)

        books = [None]
        new_path = [self.source_cell]
        for location in optimal_pick_path:
            # Introduce the location to the new path for how many ever copies of the location are in the path
            for book in locations_to_books[location]:
                books.append(book)
                new_path.append(location)

        books.append(None)
        new_path.append(self.source_cell)

        return tuple(books), tuple(new_path)

    def get_pick_path_as_dict(self, unordered_books, unordered_books_locations, ordered_books,
                              ordered_locations_optimal,
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
            'unorderedBooksAndLocations': unordered_books_and_locations,
            'orderedBooksAndLocations': ordered_books_and_locations,
            'orderedPickPath': ordered_pick_path,
        }
