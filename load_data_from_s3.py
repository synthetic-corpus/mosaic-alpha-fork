import os
import argparse
import sys
from s3_access import S3Access  # Assuming your class file is s3_access.py


def is_mounted(path):
    """Check if the specific path is a mounted volume."""
    return os.path.ismount(path)


def main():
    parser = argparse.ArgumentParser(
        description="Download video assets from S3 to EBS storage."
    )
    parser.add_argument(
        "--all-videos",
        action="store_true",
        help="Download all objects from the 'video/' prefix"
    )

    args = parser.parse_args()

    bucket_name = os.environ.get("S3_STORAGE")
    mount_point = "/mnt/ebs"
    local_target_dir = os.path.join(mount_point, "raw_vids")
    s3_prefix = "video"

    if not bucket_name:
        print("ERROR: Environment variable 'S3_STORAGE' is not set.")
        sys.exit(1)

    # Safety Check: Is the EBS volume actually there?
    if not is_mounted(mount_point):
        print(f"ERROR: EBS volume is not mounted at {mount_point}")
        print("Aborting to prevent filling up the root partition.")
        sys.exit(1)

    s3 = S3Access(bucket_name)

    if args.all_videos:
        print(f"Scanning s3://{bucket_name}/{s3_prefix}...")
        video_keys = s3.list_sources(s3_prefix)

        if not video_keys:
            print("No videos found.")
            return

        os.makedirs(local_target_dir, exist_ok=True)

        print(f"Found {len(video_keys)} objects. \
                Downloading to {local_target_dir}...")

        for key in video_keys:
            filename = os.path.basename(key)
            if not filename:  # Skips the prefix 'folder' key
                continue

            local_path = os.path.join(local_target_dir, filename)

            success = s3.download_to_disk(key, local_path)

            if not success:
                print(f"Failed to download: {key}")

        print("\nProcess Complete.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
