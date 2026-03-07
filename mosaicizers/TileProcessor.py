import os
from PIL import Image, ImageOps


class TileProcessor:
    def __init__(self, tiles_directory, tile_size=50, tile_res=5):
        self.tiles_directory = tiles_directory
        self.tile_size = tile_size,
        self.tile_block_size = tile_size / max(min(tile_res, tile_size), 1)
        self.tile_res = tile_res

    def get_average_color(self, img_path_or_obj):
        """
        The 'Resize Trick': Shrinks an image to 1x1 to find the mean RGB.
        Accepts either a file path or an existing PIL Image object.
        """
        try:
            # If it's a path, open it; otherwise assume it's an Image object
            if isinstance(img_path_or_obj, str):
                img = Image.open(img_path_or_obj)
            else:
                img = img_path_or_obj

            img = img.convert('RGB')
            # BOX resampling is fast and mathematically accurate for averaging
            img_tiny = img.resize((1, 1), resample=Image.Resampling.BOX)
            return img_tiny.getpixel((0, 0))
        except Exception as e:
            print(f"Error processing image: {e}")
            return None

    def __process_tile(self, tile_path):
        try:
            img = Image.open(tile_path)
            img = ImageOps.exif_transpose(img)

            # tiles must be square, so get the largest square that fits inside
            w = img.size[0]
            h = img.size[1]
            min_dimension = min(w, h)
            w_crop = (w - min_dimension) / 2
            h_crop = (h - min_dimension) / 2
            img = img.crop((w_crop, h_crop, w - w_crop, h - h_crop))

            large_tile_img = img.resize((self.tile_size, self.tile_size),
                                        Image.LANCZOS)
            small_tile_img = img.resize(
                (int(self.tile_size / self.tile_block_size),
                 int(self.tile_size / self.tile_block_size)),
                Image.LANCZOS
            )

            return (large_tile_img.convert('RGB'),
                    small_tile_img.convert('RGB'))
        except Exception:
            return (None, None)

    def get_tiles(self):
        large_tiles = []
        small_tiles = []
        count = 0
        exp_threshold = 1  # for logging
        print('Reading tiles from {}...'.format(self.tiles_directory))

        # search the tiles directory recursively
        for root, subFolders, files in os.walk(self.tiles_directory):
            for tile_name in files:
                tile_path = os.path.join(root, tile_name)
                large_tile, small_tile = self.__process_tile(tile_path)
                if large_tile:
                    large_tiles.append(large_tile)
                    small_tiles.append(small_tile)
                count += 1
                if count == exp_threshold:
                    print(f'Processed {count} file(s) so far...')
                    exp_threshold = exp_threshold * 2

        print('Processed {} tiles.'.format(len(large_tiles)))

        return (large_tiles, small_tiles)
