import os
import argparse
import sys
from PIL import Image
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from s3_access import S3Access
from random import shuffle

CACHE_NAME = "TILES_DATA.pkl.gz"
VENUS_CACHE_PREFIX = "venus-cache"


def resize_in_place(file_path, max_dimension=600):
    """
    Opens an image, resizes it to fit within max_dimension
    (maintaining aspect ratio), and overwrites the original file.
    """
    try:
        with Image.open(file_path) as img:
            if img.mode != 'RGB':
                # Enforces RGB for uniformity
                img = img.convert('RGB')
            # .thumbnail handles aspect ratio automatically
            # It only shrinks if the image is larger than 600px
            img.thumbnail((max_dimension, max_dimension),
                          Image.Resampling.LANCZOS)
            img.save(file_path)
            return True
    except Exception as e:
        print(f"Error resizing {file_path}: {e}")
        return False


def upload_cache(s3, local_dir):
    """
    Upload TILES_DATA.pkl.gz to the S3 venus-cache folder.

    Files larger than 8 MB are sent as a multipart upload so a cache
    over 5 GB does not hit S3's single-PUT limit.
    """
    local_path = os.path.join(local_dir, CACHE_NAME)
    s3_key = f"{VENUS_CACHE_PREFIX}/{CACHE_NAME}"
    if not os.path.isfile(local_path):
        print(f"Error: cache file {local_path} does not exist.")
        return False

    config = TransferConfig(
        multipart_threshold=8 * 1024 * 1024,
        multipart_chunksize=128 * 1024 * 1024,
        max_concurrency=10,
        use_threads=True,
    )
    print(f"Uploading {local_path} to {s3_key} with multipart upload...")
    try:
        s3.s3_client.upload_file(
            local_path,
            s3.bucket_name,
            s3_key,
            Config=config,
        )
    except ClientError as e:
        print(f"Error uploading cache to {s3_key}: {e}")
        return False

    print(f"Successfully uploaded cache to {s3_key}")
    return True


def download_cache(s3, local_dir="/mnt/ebs"):
    """
    Download TILES_DATA.pkl.gz from the S3 venus-cache folder
    into local_dir.
    """
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, CACHE_NAME)
    s3_key = f"{VENUS_CACHE_PREFIX}/{CACHE_NAME}"
    print(f"Downloading {s3_key} to {local_path}...")
    return s3.download_to_disk(s3_key, local_path)


def handle_upload(s3, local_dir, bucket_name):
    if not os.path.exists(local_dir):
        print(f"Skipping upload: {local_dir} does not exist.")
        return

    valid_images = ('.png', '.jpg', '.jpeg', '.tiff')
    print(f"Uploading results from {local_dir} to S3 \
          {bucket_name}/mosaics'...")

    for filename in os.listdir(local_dir):
        if filename.lower().endswith(valid_images):
            s3.upload_from_disk(os.path.join(local_dir, filename),
                                f"mosaics/{filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Transfer assets between S3 and EBS storage."
    )

    # Create a mutually exclusive group so only one task happens at a time
    task_group = parser.add_mutually_exclusive_group(required=True)

    task_group.add_argument(
        "--videos", action="store_true",
        help="Download video assets"
    )
    task_group.add_argument(
        "--samples", action="store_true",
        help="Download sample images (to be turned into mosaics)"
    )
    task_group.add_argument(
        "--photos", action="store_true",
        help="Download tile photos (sources for mosaic tiles)"
    )
    task_group.add_argument(
        "--upload-results", action="store_true",
        help="Upload local mosaics to S3"
    )
    task_group.add_argument(
        "--upload-cache", action="store_true",
        help="Upload TILES_DATA.pkl.gz to the S3 venus-cache folder"
    )
    task_group.add_argument(
        "--download-cache", action="store_true",
        help="Download TILES_DATA.pkl.gz from the S3 venus-cache folder"
    )

    # Shared modifiers
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit the number of files downloaded \
             (e.g., 15 for videos, 3 for samples, 100 for photos)"
    )
    parser.add_argument(
        "--out-dir", type=str, default=None,
        help="Override the default local directory"
    )
    parser.add_argument(
        "--prefix", type=str, default=None,
        help="Override the default S3 prefix (folder) to pull from"
    )

    args = parser.parse_args()

    # Configuration
    bucket_name = os.environ.get("S3_STORAGE")
    mount_point = "/mnt/ebs"

    if not bucket_name:
        print("ERROR: Environment variable 'S3_STORAGE' is not set.")
        sys.exit(1)

    s3 = S3Access(bucket_name)
    valid_extensions = ('.png', '.jpeg', '.jpg', 'webp')

    # --- Logic Based Assignment for Defaults ---
    if args.videos:
        """ Videos to become Mosaic Tiles. """
        local_dir = args.out_dir or os.path.join(mount_point, "raw_vids")
        prefix = args.prefix or "venus-videos"
        limit = args.limit or (15 if "limit" in sys.argv else None)
        is_image = False

    elif args.samples:
        """ Images to become Mosaic Tiles. """
        local_dir = args.out_dir or os.path.join(mount_point, "samples")
        prefix = args.prefix or "sample-images"
        limit = args.limit or (3 if "limit" in sys.argv else None)
        is_image = True

    elif args.photos:
        """ Images to become Mosaic Tiles. """
        local_dir = args.out_dir or os.path.join(mount_point, "raw_photos")
        prefix = args.prefix or "picsources"
        limit = args.limit or (100 if "limit" in sys.argv else None)
        is_image = True

    elif args.upload_results:
        # Upload logic is slightly different
        local_dir = args.out_dir or os.path.join(mount_point, "mosaics")
        handle_upload(s3, local_dir, bucket_name)
        return

    elif args.upload_cache:
        local_dir = args.out_dir or mount_point
        upload_cache(s3, local_dir)
        return

    elif args.download_cache:
        local_dir = args.out_dir or mount_point
        download_cache(s3, local_dir)
        return

    # --- Unified Download Execution ---
    os.makedirs(local_dir, exist_ok=True)
    print(f"Syncing S3 '{prefix}' to {local_dir}...")

    keys = s3.list_sources(prefix)

    if limit:
        shuffle(keys)
        keys = keys[:limit]

    for key in keys:
        filename = os.path.basename(key)
        if not filename:
            continue

        # Filter for images if applicable
        if is_image and not key.lower().endswith(valid_extensions):
            continue

        dest_path = os.path.join(local_dir, filename)
        s3.download_to_disk(key, dest_path)

        if is_image:
            resize_in_place(dest_path)


if __name__ == "__main__":
    main()
