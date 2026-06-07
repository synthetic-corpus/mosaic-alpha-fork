# Mosaic JTG Fork

This is a fork of the [Codebox/mosaic](https://github.com/codebox/mosaic) project. It introduces the following changes and refactors:

* **File Restructuring:** Refactored the classes of the original project from a single file into multiple, modular files.
* **Media Tools:** Provided a `tools` folder for quick pre-processing of images and slicing videos into image frames.
* **Cloud Data Sync:** Added tools for transferring photos from an Amazon S3 bucket to an EC2 instance and vice versa.
* **OpenCV Implementation:** Introduced a second version of the main application (`mosaic-v2.py`) that leverages a CV2 model rather than raw pixel processing loops.
* **KD-Tree Optimization:** Uses a KD-Tree to optimize tile matching speed, balancing computation time against target quality.

This tool generates [photo-mosaic](http://en.wikipedia.org/wiki/Photographic_mosaic) images. To use it, you must have Python installed along with the [Pillow](http://pillow.readthedocs.org/en/latest/) imaging library. 

While this version is designed assuming the code runs on an AWS EC2 instance with multiple processors, it can still be executed locally. See this blog post for [additional notes on the architecture](https://www.joelgonzaga.com/2026/05/18/photo-mosaics-with-scikit-aws-and-kdtree/).

In either case, you will need a source image for the mosaic ([most common image formats are supported](http://pillow.readthedocs.org/en/latest/handbook/image-file-formats.html)). Additionally, you will need a large collection of separate images to be used as tiles. The tile images can be any shape or size (the utility will automatically crop and resize them), but for good results, you will need at least a few hundred. One convenient way to generate a massive tile library is to [extract screenshots from video files](https://trac.ffmpeg.org/wiki/Create%20a%20thumbnail%20image%20every%20X%20seconds%20of%20the%20video) using [FFmpeg](https://www.ffmpeg.org/), which is often the quickest method for local testing.

---

## Architecture Setup (EC2, S3, and EBS)

> **Note:** This project does not provision infrastructure automatically, nor is it an exhaustive guide to AWS. Users are assumed to have a working knowledge of cloud resources or the willingness to reference official documentation. Mind your resource usage to manage costs.

Set up the following environment in AWS:
* An **S3 Bucket**
* An **EC2 Instance**
* An **EBS Volume** of a reasonable size relative to your asset library
* An **IAM Role/Instance Profile** allowing the EC2 instance to read/write to the S3 bucket

### S3 Bucket Configuration
The S3 bucket serves as your centralized storage, allowing you to easily stage raw inputs and retrieve completed mosaics. Create the following four folders:
* `tile-videos/` – Source videos to be chopped into mosaic tiles.
* `tile-images/` – Base images to be processed into mosaic tiles.
* `source-images/` – Target images you want transformed into mosaics.
* `result-mosaics/` – The destination folder where the EC2 instance drops completed outputs.

### EC2 and EBS Configuration
Using an EC2 instance optimized for compute and memory delivers the best performance, depending on your tile dataset size. 
* **4 vCPUs / 32 GB RAM** safely handles up to ~100k tiles without bottlenecking memory.
* **8 vCPUs / 64 GB RAM** is recommended for datasets scaling past 200k tiles.

The EC2 instance needs Python 3, `pip`, and public internet access to clone the project. Your attached EBS volume requires sufficient I/O performance depending on project scope.

#### Environment Setup
Clone this repository, ensure your storage volume is mounted, and install dependencies:

```bash
pip3 install -r requirements.txt
```

*(Note: Some OpenCV dependencies may take a moment to compile and install.*

The automation scripts assume an active directory path exists at /mnt/ebs/. Ensure this directory is created on your mounted volume and has read/write permissions enabled.

## Using The Tools
The tools directory contains several utility scripts. Remote into your EC2 instance via SSH and use the --help flag to inspect argument configurations:
```bash
python3 tools/splicer --help
```

## Tools Summary
- **advanced_parse.py:** An alternate method for turning videos into tile components. It captures several cropped square screenshots per frame. Use with caution due to the high volume of files generated.

- **s3_access.py:** A support file containing classes and helper methods to authenticate and connect to Amazon S3.

- **load_data_from_s3.py:** Pulls processing assets down from your S3 bucket to the local EBS drive and pushes completed renders back to S3.

- **splicer.py:** Slices raw video files into individual frames, then processes rectangular image frames into cropped square tiles. If your inputs are raw videos, you will need to execute this script for both steps.

## Making Mosaics
To use the refactored implementation of the original pixel-matching Codebox codebase, run:
```bash
python mosaic.py -file /path/to/source.jpeg -tiles /path/to/tiles_folder
```
To run the OpenCV implementation with KD-Tree optimizations, execute:
```bash
python mosaic-v2.py -file /path/to/source.jpeg -tiles /path/to/tiles_folder
```

A third alternative, `mosaic-nokd.py`, is available for comparative testing but features the longest execution time.

# Version Differences
`mosaic.py`

Functionally identical to the original Codebox engine. The CLI interface has been modified slightly for consistency, but it matches tiles to the target source image using the exact same absolute pixel-difference calculation loops.

- *Matching Behavior:* To find the optimal match for any given block, it scans every single tile in the target directory.

`mosaic-v2.py`

Matches tiles to the source image using an OpenCV computer vision approach alongside a KD-Tree to index and cluster your tile assets by their average color.

- *Matching Behavior:* When analyzing a block, it queries the KD-Tree to scan only a localized subset of optimal candidate tiles instead of the whole directory, drastically increasing rendering speeds.

- *Tile Cool-down/Randomization:* Includes a reuse penalty feature to prevent identical tiles from stacking right next to each other. The -penalty option defaults to 0.2. Higher values discourage immediate tile reuse; setting -penalty 0.0 disables randomization completely.

- *Naming Options:* Features customizable output naming flags. Run with --help to view suffix and export formatting options.

`mosaic-nokd.py`

Maintains the OpenCV processing logic found in v2, but strips away the KD-Tree color-grouping index.

- *Matching Behavior:* Because it skips the KD-Tree index and uses OpenCV, every single tile is scanned sequentially for every block. This is universally the slowest processing option of the three.

# Final Thoughts

- Running this workflow in the cloud is highly recommended due to high CPU/RAM utilization, though high-spec local workstations work perfectly as well.

- Experiment with the -penalty float parameters and alternate script versions to find the structural and visual balance you prefer.

- When using splicer.py configured to sample one frame per second, an average feature-length film yields roughly 26k–32k tiles.

- Scale Warning: The larger your asset library grows, the more memory the program requires to map out the lookup array or KD-Tree structures.
