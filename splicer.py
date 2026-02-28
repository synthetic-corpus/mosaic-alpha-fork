import cv2
import os
import hashlib
import argparse
import sys  # noqa F401 to be used later


def get_file_md5(file_path):
    """Generates an MD5 hash of the video file in chunks."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return None


def process_video(absolute_video_path, output_folder):
    """Processes a single video file."""
    cap = cv2.VideoCapture(absolute_video_path)
    if not cap.isOpened():
        print(f"  [!] Error: Could not open \
               '{os.path.basename(absolute_video_path)}'. Skipping.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0:
        print(f"  [!] Error: Could not determine FPS for \
               '{os.path.basename(absolute_video_path)}'. Skipping.")
        cap.release()
        return

    duration_seconds = total_frames / fps
    interval_seconds = 1 if duration_seconds < 60 else 5
    capture_step = int(fps * interval_seconds)

    file_hash = get_file_md5(absolute_video_path)
    saved_count = 0
    current_frame_idx = 0

    print(f"  Processing: \
           {os.path.basename(absolute_video_path)} ({duration_seconds:.1f}s)")  # noqa

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if current_frame_idx % capture_step == 0:
            saved_count += 1
            filename = f"{file_hash}-{saved_count:04d}.png"  # noqa
            save_path = os.path.join(output_folder, filename)
            cv2.imwrite(save_path, frame)

        current_frame_idx += 1

    cap.release()
    print(f"  Done. Saved {saved_count} frames.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from videos based on length.")
    parser.add_argument("-path", help="Path to a single video file.")
    parser.add_argument("-folder", help="Path to \
                         a folder to process recursively.")

    args = parser.parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, "frames")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # List to hold all files to be processed
    video_files = []

    # Handle single file mode
    if args.path:
        abs_path = os.path.abspath(args.path)
        if os.path.isfile(abs_path):
            video_files.append(abs_path)
        else:
            print(f"Error: Single file '{abs_path}' not found.")

    # Handle recursive folder mode
    if args.folder:
        abs_folder = os.path.abspath(args.folder)
        if os.path.isdir(abs_folder):
            print(f"Scanning folder: {abs_folder}...")
            for root, dirs, files in os.walk(abs_folder):
                for file in files:
                    if file.lower().endswith(".mp4"):
                        video_files.append(os.path.join(root, file))
        else:
            print(f"Error: Folder '{abs_folder}' not found.")

    if not video_files:
        print("No valid .mp4 files found to process. Use -path or -folder.")
        return

    print(f"Found {len(video_files)} video(s) to process.\n" + "-"*30)

    for vid in video_files:
        process_video(vid, output_folder)

    print("-"*30 + f"\nAll tasks complete. Frames are in: {output_folder}")


if __name__ == "__main__":
    main()
