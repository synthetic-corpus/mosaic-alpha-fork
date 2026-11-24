#!/bin/bash

export S3_STORAGE="replace-with-bucket"

# Explicitly use the python binary inside your virtual environment to ensure stability
VENV_PYTHON=".venv/bin/python3"

echo "=== Starting Test Compare at $(date) ===" > pipeline_status.log

# 1. Create the shared mount and open it up.
echo "Creating /mnt/ebs..." >> pipeline_status.log
mkdir -p /mnt/ebs || { echo "ERROR: Failed to create directory /mnt/ebs" >> pipeline_status.log; exit 1; }
chmod 777 /mnt/ebs || { echo "ERROR: Failed to chmod 777 /mnt/ebs" >> pipeline_status.log; exit 1; }

# 2. Load the tile cache.
#echo "Downloading TILES_DATA from s3..." >> pipeline_status.log
#$VENV_PYTHON -u tools/load_data_from_s3.py --download-cache > log_1_cache.log 2>&1 || { echo "ERROR: could not download TILES_DATA" >> log_1_cache.log; exit 1; }

# 3. Load the sample photos.
#echo "Downloading sample photos from s3..." >> pipeline_status.log
#$VENV_PYTHON -u tools/load_data_from_s3.py --samples > log_1_samples.log 2>&1 || { echo "ERROR: could not download sample photos" >> log_1_samples.log; exit 1; }

# 4. Original legacy mosaic.
#echo "Running mosaic.py with suffix _legacyzero..." >> pipeline_status.log
#$VENV_PYTHON -u mosaicizers/mosaic.py -folder /mnt/ebs/samples -suffix _legacyzero > log_2_legacy.log 2>&1 || { echo "ERROR: could not run mosaic.py legacy" >> log_2_legacy.log; exit 1; }

# 5. Codebox fitter, zero penalty then 0.03.
echo "Running mosaic-codebox.py with penalty 0.0..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic-codebox.py -folder /mnt/ebs/samples -penalty 0.0 -suffix _d800_p0_codebox > log_3_codebox_p0.log 2>&1 || { echo "ERROR: could not run mosaic-codebox.py p0" >> log_3_codebox_p0.log; exit 1; }

echo "Running mosaic-codebox.py with penalty 0.03..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic-codebox.py -folder /mnt/ebs/samples -penalty 0.03 -suffix _d800_p3_codebox > log_3_codebox_p3.log 2>&1 || { echo "ERROR: could not run mosaic-codebox.py p3" >> log_3_codebox_p3.log; exit 1; }

# 6. v2 fitter, same penalties and suffix pattern.
echo "Running mosaic-v2.py with penalty 0.0..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic-v2.py -folder /mnt/ebs/samples -penalty 0.0 -suffix _d800_p0_v2 > log_3_v2_p0.log 2>&1 || { echo "ERROR: could not run mosaic-v2.py p0" >> log_3_v2_p0.log; exit 1; }

echo "Running mosaic-v2.py with penalty 0.03..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic-v2.py -folder /mnt/ebs/samples -penalty 0.03 -suffix _d800_p3_v2 > log_3_v2_p3.log 2>&1 || { echo "ERROR: could not run mosaic-v2.py p3" >> log_3_v2_p3.log; exit 1; }

echo "=== Test Compare Finished Successfully at $(date) ===" >> pipeline_status.log
