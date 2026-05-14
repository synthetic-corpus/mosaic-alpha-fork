import cv2
import os
import hashlib
import argparse
import random
from multiprocessing import Pool, cpu_count
from functools import partial
from PIL import Image

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


def process_video_worker(absolute_video_path, output_folder, density=5):
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
    interval_seconds = 1 if duration_seconds < 60 else density
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


def process_image(image_path, double=True,
                  output_dir="/mnt/ebs/frames"):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with Image.open(image_path) as img:
            # Ensure RGB mode
            if img.mode != 'RGB':
                img = img.convert('RGB')

            width, height = img.size
            short_side = min(width, height)
            is_square = (width == height)

            # --- Crop 1: Upper Left ---
            upper_left_box = (0, 0, short_side, short_side)
            _save_processed_crop(img.crop(upper_left_box), output_dir)

            # --- Crop 2: Lower Right (If source not square) ---
            if double and not is_square:
                lower_right_box = (width - short_side,
                                   height - short_side,
                                   width, height)
                _save_processed_crop(img.crop(lower_right_box),
                                     output_dir)

    except Exception as e:
        print(f"Error processing {image_path}: {e}")


def _save_processed_crop(crop_img, output_dir):
    """Internal helper to resize, hash, and save the image."""
    resized = crop_img.resize((200, 200), Image.Resampling.LANCZOS)
    hash_name = hashlib.md5(resized.tobytes()).hexdigest()
    save_path = os.path.join(output_dir, f"{hash_name}.png")
    resized.save(save_path, "PNG")
    print(f"  [#] Saved: {hash_name}.png")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-threaded Media Processor")

    mode_group = parser.add_mutually_exclusive_group(required=True)

    mode_group.add_argument("-video-file",
                            help="Path to a single video file.")
    mode_group.add_argument("-video-folder",
                            help="Path to folder for recursive \
                                 video processing.")
    mode_group.add_argument("-image-folder",
                            help="Path to folder containing \
                                 images for processing.")

    parser.add_argument("-out-dir",
                        help="Override default output directory \
                             (/mnt/ebs/frames)")
    parser.add_argument("-limit", type=int,
                        help="Limit number of files processed \
                             (for testing)")
    parser.add_argument("-denisty", type=int, default=5,
                        help="In seconds, frequeence \
                              of frame capture  \
                              (> 60s always 1 second)")

    args = parser.parse_args()

    # Decalare output folder
    output_folder = args.out_dir or "/mnt/ebs/frames"
    density = args.density
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # --- BRANCH 1: IMAGE PROCESSING ---
    if args.image_folder:
        print(f"Starting Image Processing mode on: {args.image_folder}")
        abs_folder = os.path.abspath(args.image_folder)
        photos = []
        for root, _, files in os.walk(abs_folder):
            for file in files:
                extension = file.split(".")[-1]
                if extension.lower() in ["png", "jpg", "jpeg"]:
                    photos.append(os.path.join(root, file))

        if args.limit:
            random.shuffle(photos)
            photos = photos[:args.limit]

        if len(photos) == 0:
            print(f'No photos found {abs_folder}')
        for photo in photos:
            process_image(photo, double=True,
                          output_dir=output_folder)
        return

    # --- BRANCH 2: VIDEO PROCESSING ---
    video_files = []

    if args.video_file:
        video_files.append(os.path.abspath(args.video_file))

    elif args.video_folder:
        abs_folder = os.path.abspath(args.video_folder)
        for root, _, files in os.walk(abs_folder):
            for file in files:
                if file.lower().endswith(".mp4"):
                    video_files.append(os.path.join(root, file))

    if args.limit:
        random.shuffle(video_files)
        video_files = video_files[:args.limit]

    if not video_files:
        print("No videos found.")
        return

    print(f"Distributing {len(video_files)} \
          videos across {WORKER_COUNT} CPUs...")

    # --- THE MULTIPROCESSING MAGIC ---
    worker_func = partial(process_video_worker,
                          output_folder=output_folder,
                          density=density)

    with Pool(processes=WORKER_COUNT) as pool:
        for result in pool.imap_unordered(worker_func, video_files):
            print(f"  [+] {result}")

    print(f"\nProcessing complete. All frames in: {output_folder}")


if __name__ == "__main__":
    main()
