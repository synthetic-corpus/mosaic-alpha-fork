########################################################################
# The image parse makes crops based on random areas of an image
# It takes 40% area crops, and then finds the most complex
# and the most smooth. Using SSIM to identify structural complexity.
# The output is two 50x50 tiles per image, one complex and one smooth.
#########################################################################

import cv2
import numpy as np
import argparse
import os
import hashlib
import random
from skimage.metrics import structural_similarity as ssim
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing


def get_image_md5(img):
    """Generates an MD5 hash of the image pixel data."""
    return hashlib.md5(img.tobytes()).hexdigest()


def get_random_crops(img, num_crops=10):
    """Extracts N square crops of a 40% shorter dimension."""
    h, w = img.shape[:2]
    crop_size = int(min(h, w) * 0.4)

    crops = []
    for _ in range(num_crops):
        y = np.random.randint(0, h - crop_size + 1)
        x = np.random.randint(0, w - crop_size + 1)
        crops.append(img[y:y+crop_size, x:x+crop_size])
    return crops


def batch_process(source_folder, out_dir, limit=None):
    valid_exts = ('.jpg', '.jpeg', '.png')
    files = [
        os.path.join(source_folder, f) for f in os.listdir(source_folder)
        if f.lower().endswith(valid_exts)
    ]

    random.shuffle(files)
    if limit:
        files = files[:limit]

    num_cpus = multiprocessing.cpu_count()
    print(f"Launching parallel processing on {num_cpus} CPUs...")

    with ProcessPoolExecutor(max_workers=num_cpus) as executor:
        futures = {executor.submit(process_image, f, out_dir): f for f in files}  # noqa: E501

        for future in as_completed(futures):
            result = future.result()
            print(result)


def analyze_structural_complexity(crop):
    """
    Returns an SSIM score comparing the crop to a blurred version of itself.
    High Score (~1.0): Smooth / Low Detail
    Low Score (<0.5): Complex / High Detail
    """
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # 25x25 kernel provides a significant enough blur to measure structure loss
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)
    return ssim(gray, blurred)


def save_tile(crop, output_dir, suffix):
    """Resizes to 50x50, hashes, and saves to disk."""
    tile_50x50 = cv2.resize(crop, (50, 50), interpolation=cv2.INTER_AREA)
    file_hash = get_image_md5(tile_50x50)

    filename = f"{file_hash}_{suffix}.png"
    save_path = os.path.join(output_dir, filename)

    cv2.imwrite(save_path, tile_50x50)
    return save_path


def process_image(image_path, out_dir):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load {image_path}")
        return

    # 1. Generate candidate crops
    candidates = get_random_crops(img, num_crops=15)

    # 2. Score candidates
    # Store as list of (score, crop) tuples
    scored_crops = [(analyze_structural_complexity(c), c) for c in candidates]

    # 3. Identify best matches
    scored_crops.sort(key=lambda x: x[0])

    most_complex_crop = scored_crops[0][1]
    most_smooth_crop = scored_crops[-1][1]

    # 4. Save results
    output_dir = out_dir
    os.makedirs(output_dir, exist_ok=True)

    path_c = save_tile(most_complex_crop, output_dir, "complex")
    path_s = save_tile(most_smooth_crop, output_dir, "smooth")

    print(f"Success! \nComplex: {path_c} \nSmooth: {path_s}")


def main():
    parser = argparse.ArgumentParser(description="Tile extractor \
                                     with batch support.")

    parser.add_argument("--input", type=str,
                        help="Path to a single input image")
    parser.add_argument("--source-folder", type=str,
                        help="Folder containing images to process")
    parser.add_argument("--out-dir", type=str,
                        default="test_tiles", help="Where to save tiles")
    parser.add_argument("--limit", type=int,
                        help="Max number of images to process from folder")

    args = parser.parse_args()

    if args.source_folder:
        if not os.path.isdir(args.source_folder):
            print(f"Error: {args.source_folder} is not a directory.")
            return
        batch_process(args.source_folder, args.out_dir, args.limit)

    elif args.input:
        process_image(args.input, args.out_dir)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
