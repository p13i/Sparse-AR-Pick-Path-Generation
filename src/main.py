import os
import inspect
import logging
from src import utils
from src.models import GTLibraryGridWarehouse
from src import solver
from tsp import held_karp as tsp_help_karp
import numpy as np
from src import viz

# __file__ is usually defined, but not in interactive environments like this
__file__ = inspect.getfile(inspect.currentframe())

# Set up the logger
logger = logging.getLogger(os.path.basename(__file__))
logger = utils.logging.configure_logger(logger)

BOOKS_PER_PICK_PATH = 10

while True:
    # Load the warehouse object from the JSON file
    gt_library_warehouse = GTLibraryGridWarehouse.from_file('data/warehouse.json')

    logger.debug(f'Choosing {BOOKS_PER_PICK_PATH} books at random.')
    unordered_books = solver.select_unordered_books_for_picking(
        gt_library_warehouse,
        BOOKS_PER_PICK_PATH,
    )

    logger.debug(f'Getting locations of books.')
    unordered_books_locations = solver.get_locations_of_books(
        gt_library_warehouse,
        unordered_books,
    )

    logger.debug('Getting sub-graph on chosen book locations and source for TSP.')
    # If two books are on the same column, this method will consider them the same cell,
    # This is why we'll need reintroduce_duplicate_column_locations later
    G_subgraph = solver.get_induced_subgraph_on_book_locations(
        gt_library_warehouse,
        unordered_books_locations,
    )

    logger.debug('Solving TSP for selected books.')
    optimal_pick_path, optimal_cost = tsp_help_karp.solver(
        G=G_subgraph,
        source=gt_library_warehouse.source_cell,
    )

    logger.debug('Patching up solution.')
    ordered_books, ordered_locations = solver.reconstruct_library_graph(
        gt_library_warehouse,
        zip(unordered_books, unordered_books_locations),
        optimal_pick_path,
    )

    logger.debug('Ensuring variables have preserved correct lengths.')
    utils.assertions.assert_variables_have_correct_lengths(unordered_books, ordered_books, ordered_locations)

    logger.debug('Computing cell-by-cell pick path in library based on TSP solution.')
    optimal_pick_path_in_library = solver.get_pick_path_in_library(
        gt_library_warehouse,
        ordered_locations,
    )

    logger.debug('Verifying solution has right format.')
    utils.assertions.assert_correct_library_pick_path_format(
        optimal_pick_path_in_library,
        ordered_locations,
        gt_library_warehouse.source_cell,
    )

    logger.debug('Verifying solution has right cost.')
    utils.assertions.assert_library_pick_path_has_cost(
        optimal_pick_path_in_library,
        optimal_cost,
        len(ordered_books[1:-1]),
    )

    logger.debug('Packaging solution in dictionary.')
    pick_path = solver.get_pick_path_as_dict(
        path_id=1, path_type='training',
        unordered_books=unordered_books,
        unordered_books_locations=unordered_books_locations,
        ordered_books=ordered_books,
        ordered_locations_optimal=ordered_locations,
        optimal_pick_path_in_library=optimal_pick_path_in_library,
    )

    (im, output_file_path) = viz.renderer.render_gt_library_grid_warehouse(gt_library_warehouse, pick_path=pick_path)
