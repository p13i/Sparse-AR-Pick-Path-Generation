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

    def get_cell_type(self, row, col):
        """ Returns the type of the cell type at the given row and column. """
        return self.navigation_grid[row][col]

    def get_column_tag_from_row_and_col(self, row, col):
        """ Gets the column tag for the cell at the given row and column. """
        return self.navigation_grid_coordinates_to_columns_tags.get((row, col))

    def get_aisle_tag_from_column_tag(self, column_tag):
        """ Gets the aisle tag associated with the provided column tag. """
        return column_tag[0]

    def is_clear_shot(self, coordinate_a, coordinate_b, beam_radius=0.875) -> bool:
        """
        Determines if there is an unobstructed path from coordinate A to coordinate B. 'Unobstructed' is defined as a
        path with no collisions with non-NAVIGABLE_CELL cells. If the beam_radius is provided, it ensures that the clear
        shot computation is buffered on both sides of the search beam by two additional beams each one beam_radius unit
        parallel to the central search beam.
        """

        assert beam_radius > 0.0

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

                    # If the distance between central search beam and offset coordinates are less than the beam_radius...
                    if utils.distance.minimum_distance(central_search_beam_path, (new_r, new_c)) <= beam_radius:
                        # And the offset coordinates are not navigable, then...
                        if self.get_cell_type(new_r, new_c) != NavigationGridCellTypes.NAVIGABLE_CELL:
                            # Indicate that this particular search beam is not a clear shot
                            return False

        # All checks passed, this is a clear shot
        return True

    def get_navigation_grid_as_graph(self, unit_cost=1):
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
            if utils.grid.are_neighbors_in_grid(n1, n2):
                G.add_edge(n1, n2, weight=unit_cost)
                G.add_edge(n2, n1, weight=unit_cost)

        return G

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
