from PIL import Image


class TargetImage:
    def __init__(self, image_path,
                 tile_size=50, tile_res=5,
                 enlargement_factor=8):
        self.image_path = image_path
        self.tile_size = tile_size
        self.enlargement_factor = enlargement_factor
        self.tile_block_size = tile_size / max(min(tile_res, tile_size), 1)

    def get_data(self):
        print('Processing main image...')
        img = Image.open(self.image_path)
        w = img.size[0] * self.enlargement_factor
        h = img.size[1] * self.enlargement_factor
        large_img = img.resize((w, h), Image.LANCZOS)
        w_diff = (w % self.tile_size) / 2
        h_diff = (h % self.tile_size) / 2

        # crop the image slightly so we use a whole number of tiles
        if w_diff or h_diff:
            large_img = large_img.crop(
                      (w_diff, h_diff, w - w_diff, h - h_diff)
            )

        small_img = large_img.resize(
            (int(w / self.tile_block_size), int(h / self.tile_block_size)),
            Image.LANCZOS
        )

        image_data = (large_img.convert('RGB'), small_img.convert('RGB'))

        print('Main image processed.')

        return image_data
