import os
import argparse
import sys
from PIL import Image
from tools.s3_access import S3Access


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


def main():
    parser = argparse.ArgumentParser(
        description="Transfer assets between S3 and EBS storage."
    )

    parser.add_argument(
        "--all-videos",
        action="store_true",
        help="Download all objects from the 'lowresvideo' \
              prefix to /mnt/ebs/raw_vids"
    )
    parser.add_argument(
        "--all-photos",
        action="store_true",
        help="Download .png and .jpeg objects from \
              'moasic-art-photos' to /mnt/ebs/samples"
    )
    # New flag for uploading results
    parser.add_argument(
        "--upload-results",
        action="store_true",
        help="Upload all images from /mnt/ebs/mosaics \
              to the S3 'mosaics' prefix"
    )

    args = parser.parse_args()

    # Configuration from environment and paths
    bucket_name = os.environ.get("S3_STORAGE")
    mount_point = "/mnt/ebs"

    if not bucket_name:
        print("ERROR: Environment variable 'S3_STORAGE' is not set.")
        sys.exit(1)

    s3 = S3Access(bucket_name)

    # --- Logic for Videos (Download) ---
    if args.all_videos:
        local_vids_dir = os.path.join(mount_point, "raw_vids")
        os.makedirs(local_vids_dir, exist_ok=True)

        print(f"Downloading videos to {local_vids_dir}...")
        keys = s3.list_sources("lowresvideo")
        for key in keys:
            if os.path.basename(key):
                s3.download_to_disk(
                    key,
                    os.path.join(local_vids_dir, os.path.basename(key)))

    # --- Logic for Photos to be turned to mosaics (Download)
    if args.all_photos:
        local_photos_dir = os.path.join(mount_point, "samples")
        os.makedirs(local_photos_dir, exist_ok=True)

        print(f"Downloading photos to {local_photos_dir}...")
        keys = s3.list_sources("mosaic-art-photos")
        valid_extensions = ('.png', '.jpeg', '.jpg')

        for key in keys:
            if key.lower().endswith(valid_extensions):
                # downloads source files from s3
                # ensures they are never larger 600 on longer side
                filename = os.path.basename(key)
                s3.download_to_disk(
                    key, os.path.join(local_photos_dir, filename))
                resize_in_place(os.path.join(local_photos_dir, filename))

    # --- Logic for Results (Upload) ---
    if args.upload_results:
        local_mosaics_dir = os.path.join(mount_point, "mosaics")

        if not os.path.exists(local_mosaics_dir):
            print(f"Skipping upload: {local_mosaics_dir} does not exist.")
        else:
            print(f"Uploading mosaic results \
                    to S3 bucket '{bucket_name}/mosaics'...")
            valid_images = ('.png', '.jpg', '.jpeg', '.tiff')

            # Loop through the local mosaic directory
            for filename in os.listdir(local_mosaics_dir):
                if filename.lower().endswith(valid_images):
                    local_path = os.path.join(local_mosaics_dir, filename)
                    # Prepend 'mosaics/' prefix for S3
                    s3_key = f"mosaics/{filename}"

                    print(f"Uploading {filename}...")
                    s3.upload_from_disk(local_path, s3_key)

    # Show help if no flags are provided
    if not (args.all_videos or args.all_photos or args.upload_results):
        parser.print_help()


if __name__ == "__main__":
    main()
