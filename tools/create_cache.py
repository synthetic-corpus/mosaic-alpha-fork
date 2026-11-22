import os
import sys

FRAMES_DIR = "/mnt/ebs/frames"
CACHE_DIR = "/mnt/ebs"
CACHE_PATH = os.path.join(CACHE_DIR, "TILES_DATA.pkl.gz")


def frames_have_files(folder):
    """Return True when folder contains at least one file."""
    for _root, _dirs, files in os.walk(folder):
        if files:
            return True
    return False


def main():
    """Build TILES_DATA.pkl.gz from /mnt/ebs/frames and upload it."""
    tool_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(tool_dir)
    sys.path.insert(0, os.path.join(root_dir, "mosaicizers"))

    from TileProcessor import TileProcessor
    from load_data_from_s3 import upload_cache
    from s3_access import S3Access

    if not os.path.isdir(FRAMES_DIR):
        print(f"ERROR: tile folder '{FRAMES_DIR}' does not exist.")
        sys.exit(1)
    if not frames_have_files(FRAMES_DIR):
        print(f"ERROR: tile folder '{FRAMES_DIR}' has no files.")
        sys.exit(1)

    bucket_name = os.environ.get("S3_STORAGE")
    if not bucket_name:
        print("ERROR: Environment variable 'S3_STORAGE' is not set.")
        sys.exit(1)

    if os.path.exists(CACHE_PATH):
        print(f"Removing existing cache so it can be rebuilt: {CACHE_PATH}")
        os.remove(CACHE_PATH)

    print(f"Building tile cache from {FRAMES_DIR}...")
    tiles_data = TileProcessor(FRAMES_DIR).get_tiles()
    if not tiles_data or not tiles_data[0]:
        print("ERROR: no tiles were written to the cache.")
        sys.exit(1)

    print(f"Cache contains {len(tiles_data[0])} tiles.")
    s3 = S3Access(bucket_name)
    if not upload_cache(s3, CACHE_DIR):
        sys.exit(1)


if __name__ == "__main__":
    main()
