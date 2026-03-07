import io
import os
import hashlib
from PIL import Image


class MosaicImage:
    def __init__(self, original_img, tile_size=50):
        self.image = Image.new(original_img.mode, original_img.size)
        self.x_tile_count = int(original_img.size[0] / tile_size)
        self.y_tile_count = int(original_img.size[1] / tile_size)
        self.total_tiles = self.x_tile_count * self.y_tile_count
        self.tile_size = tile_size

    def add_tile(self, tile_data, coords):
        img = Image.new('RGB', (self.tile_size, self.tile_size))
        img.putdata(tile_data)
        self.image.paste(img, coords)

    def save(self, output_dir='/mnt/ebs/mosaics', suffix=''):
        """
        Saves the image_obj as a .jpeg to /mnt/ebs/mosaics
        using its MD5 hash as the filename.
        """

        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # 1. Convert image to bytes to calculate hash
        # We save to a temporary buffer or use the raw data
        img_byte_arr = io.BytesIO()
        self.image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()

        md5_hash = hashlib.md5(img_bytes).hexdigest()

        filename = f"{md5_hash}{suffix}.jpeg"
        final_path = os.path.join(output_dir, filename)

        with open(final_path, "wb") as f:
            f.write(img_bytes)

        print(f"Mosaic saved to: {final_path}")
        return final_path
