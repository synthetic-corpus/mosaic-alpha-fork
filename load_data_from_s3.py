import os
import argparse
import sys
from s3_access import S3Access


def is_mounted(path):
    """Check if the specific path is a mounted volume."""
    return os.path.ismount(path)


def main():
    parser = argparse.ArgumentParser(
        description="Transfer assets from S3 to EBS storage."
    )

    parser.add_argument(
        "--all-videos",
        action="store_true",
        help="Download all objects from \
              the 'video/' prefix to /mnt/ebs/raw_vids"
    )
    parser.add_argument(
        "--all-photos",
        action="store_true",
        help="Download .png and .jpeg \
              objects from 'photos/' to /mnt/ebs/samples"
    )

    args = parser.parse_args()

    bucket_name = os.environ.get("S3_STORAGE")
    mount_point = "/mnt/ebs"

    if not bucket_name:
        print("ERROR: Environment variable 'S3_STORAGE' is not set.")
        sys.exit(1)

    if not is_mounted(mount_point):
        print(f"ERROR: EBS volume is not mounted at {mount_point}")
        sys.exit(1)

    s3 = S3Access(bucket_name)

    # Logic for Videos
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

    # Logic for Photos. Get the phots we'll make mosaics from
    if args.all_photos:
        local_photos_dir = os.path.join(mount_point, "samples")
        os.makedirs(local_photos_dir, exist_ok=True)

        print(f"Downloading photos to {local_photos_dir}...")
        keys = s3.list_sources("moasic-art-photos")

        valid_extensions = ('.png', '.jpeg', '.jpg')

        for key in keys:
            if key.lower().endswith(valid_extensions):
                filename = os.path.basename(key)
                s3.download_to_disk(
                    key, os.path.join(local_photos_dir, filename))

    if not (args.all_videos or args.all_photos):
        parser.print_help()


if __name__ == "__main__":
    main()
