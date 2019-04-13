try:
    import Tkinter as tk
except ImportError:
    import tkinter as tk

import logging
from src import utils
import os
from PIL import Image, ImageDraw, ImageFont
from src import viz

logger = logging.getLogger(os.path.basename(__file__))
logger = utils.logging.configure_logger(logger)

PICK_PATH_FILE_FORMAT_VERSION = '2.0'

# The length of a side on each square in the Tkinter window
SQUARE_SIDE_LENGTH_PX = 50  # best: 35

# Width of the gridlines
GRID_LINE_WIDTH = 5

# Font size used in all text
DEFAULT_FONT_SIZE = 12

# The height of text
DEFAULT_TEXT_HEIGHT_PX = 30

# The height of the legend at the bottom of the screen
# 8 = (number of items in legend) + (padding) = 7 + 1
LEGEND_HEIGHT_PX = 8 * DEFAULT_TEXT_HEIGHT_PX

# Height of title text at bottom of screen
TITLE_TEXT_HEIGHT_PX = DEFAULT_TEXT_HEIGHT_PX

# Padding for text on the left side
TEXT_PADDING_LEFT_PX = 10


class Colors(str):
    """
    Colors based on "Apple Human Interface Guidelines - Colors"
    (https://developer.apple.com/ios/human-interface-guidelines/visual-design/color/)
    """

    # Graphic colors
    NAVIGABLE_CELL = '#fff'     # white
    OBSTACLE_CELL = '#aaa'      # light gray
    SHELVE_CELL = '#ffcc00'     # yellow-orange
    PATH_CELL = '#007aff'       # blue
    TARGET_BOOK_CELL = '#543aff'# purple

    CHEVRON = '#ff3b30'         # red
    PATH_LINE = '#ff8b84'       # light red

    TITLE_FONT = '#5856d6'      # purple
    COLUMN_LINE = '#aaaaaa'     # light gray


def render_gt_library_grid_warehouse(
        gt_library_grid_warehouse,
        pick_path=None,
    ):

    from src.models import NavigationGridCellTypes

    canvas_width = gt_library_grid_warehouse.num_cols * SQUARE_SIDE_LENGTH_PX
    canvas_height = gt_library_grid_warehouse.num_rows * SQUARE_SIDE_LENGTH_PX + LEGEND_HEIGHT_PX + TITLE_TEXT_HEIGHT_PX

    im = Image.new(
        mode='RGBA',
        size=(canvas_width, canvas_height)
    )
    canvas = ImageDraw.Draw(im)

    # Setup pick path

    """ Renders the given pick path on the provided grid warehouse into Tkinter main window. """

    logger.info('Starting render...')

    # Draw obstacles, shelves, and navigable cells
    for r in range(gt_library_grid_warehouse.num_rows):
        for c in range(gt_library_grid_warehouse.num_cols):
            cell = gt_library_grid_warehouse.get_cell_type(r, c)

            # Get the right cell color based on the cell's type
            if cell == NavigationGridCellTypes.SHELVE_CELL:
                color = Colors.SHELVE_CELL
            elif cell == NavigationGridCellTypes.NAVIGABLE_CELL:
                color = Colors.NAVIGABLE_CELL
            elif cell == NavigationGridCellTypes.OBSTACLE_CELL:
                color = Colors.OBSTACLE_CELL
            else:
                raise ValueError(f'Unknown cell type {cell}')

            canvas.rectangle([
                (c * SQUARE_SIDE_LENGTH_PX, r * SQUARE_SIDE_LENGTH_PX),
                ((c + 1) * SQUARE_SIDE_LENGTH_PX, (r + 1) * SQUARE_SIDE_LENGTH_PX)],
                fill=color,
            )

    logger.debug('Drew all cells with appropriate colors.')


    # Draw column lines
    for col_idx in range(gt_library_grid_warehouse.num_cols):
        col_px = col_idx * SQUARE_SIDE_LENGTH_PX
        canvas.line([(col_px, 0), (col_px, canvas_height - DEFAULT_TEXT_HEIGHT_PX)], fill=Colors.COLUMN_LINE, width=GRID_LINE_WIDTH)

    logger.debug('Drew column lines.')

    # Draw row lines
    for row_idx in range(gt_library_grid_warehouse.num_rows):
        row_px = row_idx * SQUARE_SIDE_LENGTH_PX
        canvas.line([(0, row_px), (canvas_width, row_px)], fill=Colors.COLUMN_LINE, width=GRID_LINE_WIDTH)

    logger.debug('Drew row lines.')

    if pick_path:
        # Get pick path to be rendered
        ordered_pick_path = pick_path['pickPathInformation']['orderedPickPath']

        chevron_count = 0
        # Draw chevrons and path direction lines
        for path_component in ordered_pick_path:
            cell_by_cell_path_to_target_book_location = path_component['cellByCellPathToTargetBookLocation']

            # Draw the cell
            # Ignore first and last elements of cell-by-cell path because they are repeated between consecutive paths
            for i, current_cell in enumerate(cell_by_cell_path_to_target_book_location[1:-1]):

                current_cell_r, current_cell_c = current_cell

                # Draw cell in the path
                canvas.rectangle([
                    (current_cell_c * SQUARE_SIDE_LENGTH_PX, current_cell_r * SQUARE_SIDE_LENGTH_PX),
                    ((current_cell_c + 1) * SQUARE_SIDE_LENGTH_PX, (current_cell_r + 1) * SQUARE_SIDE_LENGTH_PX)],
                    fill=Colors.CHEVRON,
                )


            target_location = path_component['targetBookAndTargetBookLocation']['location']
            if target_location:
                target_location_r, target_location_c = target_location

                canvas.rectangle(
                    [(target_location_c * SQUARE_SIDE_LENGTH_PX, target_location_r * SQUARE_SIDE_LENGTH_PX),
                     ((target_location_c + 1) * SQUARE_SIDE_LENGTH_PX,
                      (target_location_r + 1) * SQUARE_SIDE_LENGTH_PX)],
                    fill=Colors.TARGET_BOOK_CELL)


        # Draw the paths/chevrons
        for path_component in ordered_pick_path:
            cell_by_cell_path_to_target_book_location = path_component['cellByCellPathToTargetBookLocation']

            for i, current_cell in enumerate(cell_by_cell_path_to_target_book_location):
                current_cell_r, current_cell_c = current_cell

                # If there is a next cell (we're not at the end) render the arrow and path line
                if i >= len(cell_by_cell_path_to_target_book_location) - 1:
                    continue

                next_cell = cell_by_cell_path_to_target_book_location[i + 1]
                next_cell_r, next_cell_c = next_cell

                path_start = ((current_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX, (current_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX)
                path_end = ((next_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX, (next_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX)

                path = path_start, path_end
                path = viz.path.adjust_path(path, by_px=SQUARE_SIDE_LENGTH_PX // 10, direction='right')


                # Draw line between these two points
                canvas.line(
                    path,
                    fill=Colors.PATH_LINE,
                    width=GRID_LINE_WIDTH,
                    # activedash=True,
                    # dash=True,
                    # width=SQUARE_SIDE_LENGTH_PX / 5
                )

                direction = viz.chevron.get_chevron_angle_transform_for_coordinates(*path)

                triangle_points = viz.chevron.get_transformed_chevron(
                    origin=path_start,
                    transform_angle=direction,
                    square_side_length=SQUARE_SIDE_LENGTH_PX,
                )

                # Transform centroid 20% onto the path line
                new_chevron_centroid = viz.geometry.calculate_point_on_path(path, ratio_onto_path=0.40)
                triangle_points = viz.chevron.translate_polygon_to(triangle_points, new_chevron_centroid)

                canvas.polygon(
                    triangle_points,
                    fill=Colors.CHEVRON,)

                chevron_count += 1
                canvas.text(new_chevron_centroid, str(chevron_count), font=ImageFont.load_default())


        logger.debug('Drew pick path.')
    else:
        logger.warning('No pick path provided.')

    # Draw legend
    canvas.rectangle(
        [(TEXT_PADDING_LEFT_PX, canvas_height - LEGEND_HEIGHT_PX),
         (200, canvas_height - TITLE_TEXT_HEIGHT_PX)],
        fill='BLACK',
    )

    # Draw pick path ID
    if pick_path:
        title_text = 'Path ID %02d - %s' % (pick_path['pathId'], pick_path['pathType'].title())
    else:
        title_text = ''
    canvas.text(
        (TEXT_PADDING_LEFT_PX, canvas_height - LEGEND_HEIGHT_PX - DEFAULT_TEXT_HEIGHT_PX / 2),
        # anchor=tk.W,
        fill=Colors.TITLE_FONT,
        font=ImageFont.load_default(),
        text=title_text)

    logger.debug('Drew title.')

    logger.info('Finished render.')

    im.save('test.png', format='png', compress_level=0)

    return 'test.png'
