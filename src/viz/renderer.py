try:
    import Tkinter as tk
except ImportError:
    import tkinter as tk

import logging
from src import utils
import json
import os
from PIL import Image
import io
from src import viz

logger = logging.getLogger(os.path.basename(__file__))
logger = utils.logging.configure_logger(logger)

PICK_PATH_FILE_FORMAT_VERSION = '2.0'

# The length of a side on each square in the Tkinter window
SQUARE_SIDE_LENGTH_PX = 100  # best: 35

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
    TARGET_BOOK_CELL = '#4cd964'# green

    CHEVRON = '#ff3b30'         # red
    PATH_LINE = CHEVRON

    TITLE_FONT = '#5856d6'      # purple



def render_gt_library_grid_warehouse(
        gt_library_grid_warehouse,
        pick_path=None,
    ):

    from src.models import NavigationGridCellTypes

    canvas_width = gt_library_grid_warehouse.num_cols * SQUARE_SIDE_LENGTH_PX
    canvas_height = gt_library_grid_warehouse.num_rows * SQUARE_SIDE_LENGTH_PX + LEGEND_HEIGHT_PX + TITLE_TEXT_HEIGHT_PX

    # Tkinter setup
    tk_main = tk.Tk()

    canvas = tk.Canvas(
        master=tk_main,
        width=canvas_width,
        height=canvas_height,
    )
    canvas.pack()
    canvas.master.title("Sparse AR - Pick Path Visualization - v%s" % PICK_PATH_FILE_FORMAT_VERSION)

    # Setup pick path

    """ Renders the given pick path on the provided grid warehouse into Tkinter main window. """

    logger.info('Starting render...')

    # Rely on global variables that can be modified elsewhere
    # global gt_library_grid_warehouse, canvas_height, canvas_width, canvas, pick_paths, current_pick_path_index

    # Remove all elements added in previous calls to render
    canvas.delete('all')
    logger.debug('Cleared previous elements from canvas.')

    # Draw column lines
    for col_idx in range(gt_library_grid_warehouse.num_cols):
        col_px = col_idx * SQUARE_SIDE_LENGTH_PX
        canvas.create_line(col_px, 0, col_px, canvas_height - DEFAULT_TEXT_HEIGHT_PX)

    logger.debug('Drew column lines.')

    # Draw row lines
    for row_idx in range(gt_library_grid_warehouse.num_rows):
        row_px = row_idx * SQUARE_SIDE_LENGTH_PX
        canvas.create_line(0, row_px, canvas_width, row_px)

    logger.debug('Drew row lines.')

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

            canvas.create_rectangle(
                c * SQUARE_SIDE_LENGTH_PX,
                r * SQUARE_SIDE_LENGTH_PX,
                (c + 1) * SQUARE_SIDE_LENGTH_PX,
                (r + 1) * SQUARE_SIDE_LENGTH_PX,
                fill=color,
            )

    logger.debug('Drew all cells with appropriate colors.')

    if pick_path:
        # Get pick path to be rendered
        ordered_pick_path = pick_path['pickPathInformation']['orderedPickPath']

        # Draw pick paths
        for path_component in ordered_pick_path:
            cell_by_cell_path_to_target_book_location = path_component['cellByCellPathToTargetBookLocation']

            for i, current_cell in enumerate(cell_by_cell_path_to_target_book_location):
                current_cell_r, current_cell_c = current_cell

                # Draw cell in the path
                canvas.create_rectangle(
                    current_cell_c * SQUARE_SIDE_LENGTH_PX,
                    current_cell_r * SQUARE_SIDE_LENGTH_PX,
                    (current_cell_c + 1) * SQUARE_SIDE_LENGTH_PX,
                    (current_cell_r + 1) * SQUARE_SIDE_LENGTH_PX,
                    fill=Colors.PATH_CELL,
                )

        # Draw chevrons and path direction lines
        for path_component in ordered_pick_path:
            cell_by_cell_path_to_target_book_location = path_component['cellByCellPathToTargetBookLocation']

            for i, current_cell in enumerate(cell_by_cell_path_to_target_book_location):
                current_cell_r, current_cell_c = current_cell

                # If there is a next cell (we're not at the end) render the arrow and path line
                if i >= len(cell_by_cell_path_to_target_book_location) - 1:
                    continue

                next_cell = cell_by_cell_path_to_target_book_location[i + 1]
                next_cell_r, next_cell_c = next_cell
                direction = viz.chevron.get_chevron_angle_transform_for_coordinates(
                    a=(
                        (current_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX, (current_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX),
                    b=((next_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX, (next_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX))

                triangle_points = viz.chevron.get_transformed_chevron(origin=(
                    (current_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX,  # x
                    (current_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX,  # y
                ), transform_angle=direction, square_side_length=SQUARE_SIDE_LENGTH_PX)

                canvas.create_polygon(
                    *triangle_points,
                    fill=Colors.CHEVRON)

                # Draw line between these two points
                canvas.create_line(
                    (current_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX,  # x
                    (current_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX,  # y
                    (next_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX,
                    (next_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX,
                    fill=Colors.PATH_LINE,
                    activedash=True,
                    dash=True,
                    width=SQUARE_SIDE_LENGTH_PX / 5
                )

        logger.debug('Drew chevron and path direction lines.')

        # Draw target books
        for path_component in ordered_pick_path:
            target_book_and_location = path_component['targetBookAndTargetBookLocation']
            target_location = target_book_and_location['location']

            if not target_location:
                continue

            target_location_r, target_location_c = target_book_and_location['location']

            canvas.create_rectangle(
                target_location_c * SQUARE_SIDE_LENGTH_PX,
                target_location_r * SQUARE_SIDE_LENGTH_PX,
                (target_location_c + 1) * SQUARE_SIDE_LENGTH_PX,
                (target_location_r + 1) * SQUARE_SIDE_LENGTH_PX,
                fill=Colors.TARGET_BOOK_CELL)

        logger.debug('Drew target books.')

        logger.debug('Drew pick path.')
    else:
        logger.warning('No pick path provided.')

    # Draw legend
    canvas.create_rectangle(
        TEXT_PADDING_LEFT_PX,
        canvas_height - LEGEND_HEIGHT_PX,
        200,
        canvas_height - TITLE_TEXT_HEIGHT_PX,
        fill='BLACK',
    )

    # Draw pick path ID
    canvas.create_text(
        TEXT_PADDING_LEFT_PX,  # x offset
        canvas_height - LEGEND_HEIGHT_PX - DEFAULT_TEXT_HEIGHT_PX / 2,
        anchor=tk.W,
        fill=Colors.TITLE_FONT,
        font=f'Calibri {DEFAULT_FONT_SIZE} bold',
        text='Path ID %02d - %s' % (pick_path['pathId'], pick_path['pathType'].title()))

    logger.debug('Drew title.')

    # Apply changes to canvas
    canvas.update()

    logger.info('Finished render.')

    ps = canvas.postscript(colormode='color')
    img = Image.open(io.BytesIO(ps.encode('utf-8')))
    img.save('test.png', format='png', compress_level=0)

    tk_main.quit()
    tk_main.destroy()

    return 'test.png'
