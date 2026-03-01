import cv2
import os
import hashlib
import argparse
from multiprocessing import Pool, cpu_count
from functools import partial

WORKER_COUNT = cpu_count()


def is_video_readable(v_path):
    """ Verifies if a file is not corrupted """
    cap = cv2.VideoCapture(v_path)
    if not cap.isOpened():
        return False

    # Try to grab just the first frame to see if the decoder barfs
    ret, frame = cap.read()
    cap.release()

    return ret and frame is not None


def get_file_md5(file_path):
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None


def resize_maintain_aspect(frame, short_side_target=200):
    h, w = frame.shape[:2]
    if h < w:
        ratio = short_side_target / float(h)
        new_dim = (int(w * ratio), short_side_target)
    else:
        ratio = short_side_target / float(w)
        new_dim = (short_side_target, int(h * ratio))
    return cv2.resize(frame, new_dim, interpolation=cv2.INTER_AREA)


def process_video_worker(absolute_video_path, output_folder):
    """The function each CPU core will run."""
    if not is_video_readable(absolute_video_path):
        return f"Error: {os.path.basename(absolute_video_path)}\
                is not readable!"
    cap = cv2.VideoCapture(absolute_video_path)
    if not cap.isOpened():
        return f"Error: {os.path.basename(absolute_video_path)}"

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0:
        cap.release()
        return f"Bad FPS: {os.path.basename(absolute_video_path)}"

    duration_seconds = total_frames / fps
    interval_seconds = 1 if duration_seconds < 60 else 5
    capture_step = int(fps * interval_seconds)

    file_hash = get_file_md5(absolute_video_path)
    saved_count = 0
    current_frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if current_frame_idx % capture_step == 0:
            saved_count += 1
            filename = f"{file_hash}-{saved_count:04d}.png"
            processed_frame = resize_maintain_aspect(frame,
                                                     short_side_target=200)
            save_path = os.path.join(output_folder, filename)
            cv2.imwrite(save_path, processed_frame)

        current_frame_idx += 1

    cap.release()
    return f"Done: {os.path.basename(absolute_video_path)} \
             ({saved_count} frames)"


def main():
    parser = argparse.ArgumentParser(
        description="Multi-threaded Frame Extraction")
    parser.add_argument("-path",
                        help="Path to a single video file.")
    parser.add_argument("-folder",
                        help="Path to folder for recursive processing.")
    args = parser.parse_args()

    output_folder = os.path.join('/mnt/ebs/', "frames")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video_files = []
    if args.path:
        video_files.append(os.path.abspath(args.path))
    if args.folder:
        abs_folder = os.path.abspath(args.folder)
        for root, _, files in os.walk(abs_folder):
            for file in files:
                if file.lower().endswith(".mp4"):
                    video_files.append(os.path.join(root, file))

    if not video_files:
        print("No videos found.")
        return

    print(f"Distributing {len(video_files)} \
            videos across {WORKER_COUNT} CPUs...")

    # --- THE MULTIPROCESSING MAGIC ---
    worker_func = partial(process_video_worker,
                          output_folder=output_folder)

    with Pool(processes=WORKER_COUNT) as pool:
        # 'imap_unordered' for easy balanacing
        for result in pool.imap_unordered(worker_func, video_files):
            print(f"  [+] {result}")

    print(f"\nProcessing complete. All frames in: {output_folder}")


if __name__ == "__main__":
    main()
