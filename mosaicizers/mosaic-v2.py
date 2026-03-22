###############################################
# This file will create a mosaic from CLI.
# TODO need to sort out functions here
# In a new extension of Mosaic.
###############################################

import os
import os.path
import argparse
from multiprocessing import Queue, cpu_count, get_context

# These are the custom imports
from MosaicImage import MosaicImage
from TargetImage import TargetImage
from TileProcessor import TileProcessor
from TileFitterSciKit import TileFitterSciKit
from ProgressCounter import ProgressCounter

# These are now configed by CLI or class defaults
TILE_SIZE = 50     # height/width of mosaic tiles in pixels
TILE_MATCH_RES = 5      # tile matching resolution
# ENLARGEMENT = 8      # mosaic image will be this many times larger
# Image.MAX_IMAGE_PIXELS = None  # Dangerous, but allow it for now

TILE_BLOCK_SIZE = TILE_SIZE / max(min(TILE_MATCH_RES, TILE_SIZE), 1)
WORKER_COUNT = max(cpu_count() - 1, 1)
# OUT_FILE = 'mosaic.jpeg'
EOQ_VALUE = None


_global_fitter = None  # Shared across all workers


def worker_init(tile_data, penalty):
    """This runs ONCE when each worker process starts."""
    global _global_fitter
    _global_fitter = TileFitterSciKit(tile_data, penalty=penalty)


def worker_task(work_queue, result_queue):
    """The actual loop the worker runs."""
    # Use the global fitter already sitting in this process's memory
    _global_fitter.fit_tiles(work_queue, result_queue)


def compose(original_img, tiles, penalty=0.2, suffix=''):
    print('Building mosaic, press Ctrl-C to abort...')
    original_img_large, original_img_small = original_img
    tiles_large, tiles_small = tiles

    # 1. Initialize our mosaic object
    mosaic = MosaicImage(original_img_large)

    all_tile_data_large = [list(tile.getdata()) for tile in tiles_large]
    all_tile_data_small = [list(tile.getdata()) for tile in tiles_small]

    work_queue = Queue()
    result_queue = Queue()

    # 2a Init the Global Fitter.
    worker_init(all_tile_data_small, penalty)
    ctx = get_context('fork')  # from an import at the top
    worker_pool = []
    # 2b Rally workers.
    for n in range(WORKER_COUNT):
        p = ctx.Process(
            target=worker_task,
            args=(work_queue, result_queue)
        )
        p.start()
        worker_pool.append(p)

    try:
        # 3. Phase 1: Dispatch work (The Producer)
        progress = ProgressCounter(mosaic.x_tile_count * mosaic.y_tile_count)
        for x in range(mosaic.x_tile_count):
            for y in range(mosaic.y_tile_count):
                # ... [Your existing cropping logic here] ...
                large_box = (x * TILE_SIZE, y * TILE_SIZE,
                             (x + 1) * TILE_SIZE, (y + 1) * TILE_SIZE)
                small_box = (x * TILE_SIZE / TILE_BLOCK_SIZE,
                             y * TILE_SIZE / TILE_BLOCK_SIZE,
                             (x + 1) * TILE_SIZE / TILE_BLOCK_SIZE,
                             (y + 1) * TILE_SIZE / TILE_BLOCK_SIZE)

                work_queue.put(
                    (list(original_img_small.crop(small_box).getdata()),
                     large_box))
                progress.update()

        # 4. Phase 2: Collect and Paste (The Consumer)
        # We call this in the MAIN process. It will block here until
        # the workers finish sending results through the result_queue.

    except KeyboardInterrupt:
        print('\nHalting, saving partial image please wait...')
        # We tell the workers to stop
        for n in range(WORKER_COUNT):
            work_queue.put((EOQ_VALUE, EOQ_VALUE))

    finally:
        # Ensure workers are cleaned up
        for p in worker_pool:
            if p.is_alive():
                work_queue.put((EOQ_VALUE, EOQ_VALUE))

        mosaic.assemble(result_queue, all_tile_data_large,
                        WORKER_COUNT)
        mosaic.save(suffix=suffix)


def show_error(msg):
    print('ERROR: {}'.format(msg))


def mosaic(img_path, tiles_data, penalty=0.2, suffix=''):
    """ Takes in Tiles Data as an Agrument now """
    image_data = TargetImage(img_path).get_data()
    # tiles_data = TileProcessor(tiles_path).get_tiles()
    if tiles_data[0]:
        compose(image_data, tiles_data, penalty=penalty, suffix=suffix)
    else:
        show_error("Tiles Data not propery formatted!")


if __name__ == '__main__':
    def restricted_float(x):
        try:
            x = float(x)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{x} is not a \
                                              floating-point number")

        if x < 0.0 or x > 0.5:
            raise argparse.ArgumentTypeError(f"{x} is not in range \
                                             [0.01, 0.5]")
        return x

    parser = argparse.ArgumentParser(
        description="Generate a high-quality mosaic.")

    # Create the mutually exclusive group for input
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-file", "-f", help="Path to the source image file.")
    group.add_argument("-folder", help="Path to a \
                       folder of images (not yet implemented).")

    # The tiles directory with a default value
    parser.add_argument("-tiles", "-t",
                        default="/mnt/ebs/frames",
                        help="Path to the directory \
                              containing tiles (default: /mnt/ebs/frames)")

    parser.add_argument("-out_dir", "-o",
                        default="/mnt/ebs/mosaics",
                        help="This is the directory the \
                              Mosaics will be save to.")

    parser.add_argument('-suffix', '-s',
                        help="Type something here if \
                              if you want it appended \
                              to the file name.")

    parser.add_argument('-penalty',
                        type=restricted_float,
                        default=0.2,
                        help="Set the penalty (range: 0.0 to 0.5, \
                              default: 0.2) \
                              High Penalty means less repetition of tiles")
    args = parser.parse_args()

    # Current logic: Only handle the single file mode
    if args.file:
        source_image = os.path.abspath(args.file)
        tile_dir = os.path.abspath(args.tiles)

        if not os.path.isfile(source_image):
            show_error(f"Unable to find image file '{source_image}'")
        elif not os.path.isdir(tile_dir):
            show_error(f"Unable to find tile directory '{tile_dir}'")
        else:
            # Trigger the mosaic process
            tiles_data = TileProcessor(tile_dir).get_tiles()
            mosaic(source_image, tiles_data,
                   penalty=args.penalty, suffix=args.suffix)

    elif args.folder:
        abs_folder = os.path.abspath(args.folder)
        tile_dir = os.path.abspath(args.tiles)
        try:
            samples = [e.path for e in os.scandir(abs_folder)
                       if e.is_file()]
        except FileNotFoundError:
            print(f"Error: Folder '{abs_folder}' not found.")
            exit(1)
        try:
            tp = TileProcessor(tile_dir)
            tiles_data = tp.get_tiles()
        except FileNotFoundError:
            print(f"Error: Tile directory '{tile_dir}' not found.")
            exit(1)
        except Exception as e:
            print(f"Error running TileProcessor class '{tile_dir}': {e}")
            exit(1)
        for file_path in samples:
            if not os.path.isfile(file_path):
                show_error(f"Unable to find image file \
                           '{file_path}'")
                continue
            elif not os.path.isdir(tile_dir):
                show_error(f"Unable to find tile directory \
                           '{tile_dir}'")
                continue
            else:
                # Trigger the mosaic process
                mosaic(file_path, tiles_data,
                       penalty=args.penalty, suffix=args.suffix)
