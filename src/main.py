import os
import inspect
import logging
from src import utils
from src.models import GTLibraryGridWarehouse
from tsp import held_karp as tsp_help_karp
import numpy as np
from src import viz
import json
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

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
    unordered_books = np.random.choice(
        a=gt_library_warehouse.books,
        size=BOOKS_PER_PICK_PATH,
        replace=False,
    )

    unordered_books_locations = gt_library_warehouse.get_locations_of_books(unordered_books)

    logger.debug('Getting sub-graph on chosen book locations and source for TSP.')
    # If two books are on the same column, this method will consider them the same cell,
    # This is why we'll need reintroduce_duplicate_column_locations later
    G_subgraph = gt_library_warehouse.get_subgraph_on_book_locations(unordered_books_locations)

    logger.debug('Solving TSP for selected books.')
    optimal_pick_path, optimal_cost = tsp_help_karp.solver(G_subgraph, gt_library_warehouse.source_cell)

    logger.debug('Patching up solution.')
    ordered_books, ordered_locations = gt_library_warehouse.reintroduce_duplicate_column_locations(
        zip(unordered_books, unordered_books_locations), optimal_pick_path)

    # The optimal pick path has two more source locations (source, ..., source)
    assert len(unordered_books) == len(ordered_books) - 2 == len(ordered_locations) - 2

    logger.debug('Computing cell-by-cell pick path in library based on TSP solution.')
    optimal_pick_path_in_library = gt_library_warehouse.get_pick_path_in_library(ordered_locations)

    logger.debug('Verifying solution has right format and cost.')
    utils.assertions.assert_library_pick_path_is_proper(
        optimal_pick_path_in_library, ordered_locations, gt_library_warehouse.source_cell)
    utils.assertions.assert_library_pick_path_has_cost(
        optimal_pick_path_in_library, optimal_cost, len(ordered_books[1:-1]))

    logger.debug('Packaging solution in dictionary.')
    pick_path = gt_library_warehouse.get_pick_path_as_dict(
        1,
        'training',
        unordered_books,
        unordered_books_locations,
        ordered_books,
        ordered_locations,
        optimal_pick_path_in_library,
    )

    path = viz.renderer.render_gt_library_grid_warehouse(gt_library_warehouse, pick_path=pick_path)

    # https://pages.uoregon.edu/koch/

    # im = mpimg.imread(path)
    # height, width = im.shape[:2]
    # fig, ax = plt.subplots(figsize=(15, 15))
    # ax.imshow(im)
