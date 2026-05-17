import os
import argparse
import sys
from PIL import Image
from s3_access import S3Access
from random import shuffle


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
        local_dir = args.out_dir or os.path.join(mount_point, "raw_vids")
        prefix = args.prefix or "lowresvideo"
        limit = args.limit or (15 if "limit" in sys.argv else None)
        is_image = False

    elif args.samples:
        local_dir = args.out_dir or os.path.join(mount_point, "samples")
        prefix = args.prefix or "mosaic-art-photos"
        limit = args.limit or (3 if "limit" in sys.argv else None)
        is_image = True

    elif args.photos:
        local_dir = args.out_dir or os.path.join(mount_point, "raw_photos")
        prefix = args.prefix or "picsources"
        limit = args.limit or (100 if "limit" in sys.argv else None)
        is_image = True

    elif args.upload_results:
        # Upload logic is slightly different
        local_dir = args.out_dir or os.path.join(mount_point, "mosaics")
        handle_upload(s3, local_dir, bucket_name)
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
