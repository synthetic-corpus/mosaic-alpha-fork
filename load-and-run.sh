#!/bin/bash

export S3_STORAGE="replace-with-bucket"

# Explicitly use the python binary inside your virtual environment to ensure stability
VENV_PYTHON=".venv/bin/python3"

echo "=== Starting Pipeline at $(date) ===" > pipeline_status.log

# 1. Make the directory that everything saves to and reads from.
#echo "Creating Source directory." >> pipeline_status.log
#mkdir -p /mnt/ebs || { echo "ERROR: Failed to create directory /mnt/ebs" >> pipeline_status.log; exit 1; }
#chmod 777 /mnt/ebs || { echo "ERROR: Failed to 777 /mnt/ebs" >> pipeline_status.log; exit 1; }

# 2. Download Step (Changed second command to >> to append)
echo "Downloading from videos s3..." >> pipeline_status.log
$VENV_PYTHON -u tools/load_data_from_s3.py --videos > log_0_download.log 2>&1 || { echo "ERROR: could not download videos" >> log_0_download.log; exit 1; }

echo "Downloading from samples s3..." >> pipeline_status.log
$VENV_PYTHON -u tools/load_data_from_s3.py --samples >> log_0_download.log 2>&1 || { echo "ERROR: could not download source photos" >> log_0_download.log; exit 1; }

# 3. Preprocessing Steps (Sequential - Changed second to >> and fixed error strings)
echo "Running preprocess step 1 (splicer vids)..." >> pipeline_status.log
$VENV_PYTHON -u tools/splicer.py -video-folder /mnt/ebs/raw_vids -out-dir /mnt/ebs/raw_photos > log_1_preprocess.log 2>&1 || { echo "ERROR: failed to splice videos" >> log_1_preprocess.log; exit 1; }

echo "Running preprocess step 2 (splicer photos)..." >> pipeline_status.log
$VENV_PYTHON -u tools/splicer.py -image-folder /mnt/ebs/raw_photos >> log_1_preprocess.log 2>&1 || { echo "ERROR: failed to process photos" >> log_1_preprocess.log; exit 1; }

# 4. Main Processing Iterations (Sequential - Using unique log files per variation for easier debugging)
echo "Running process with legacy method..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic.py -folder /mnt/ebs/samples > log_2_legacy.log 2>&1 || { echo "ERROR: could not run legacy mosaics.py" >> log_2_legacy.log; exit 1; }

echo "Running main script v2 with no penalty..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic-v2.py -folder /mnt/ebs/samples -penalty 0.0 -suffix _p00_v2 > log_3_v2_p00.log 2>&1 || { echo "ERROR: could not run mosaics-v2.py p00" >> log_3_v2_p00.log; exit 1; }

echo "Running main script v2 with low penalty..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic-v2.py -folder /mnt/ebs/samples -penalty 0.05 -suffix _p05_v2 > log_3_v2_p05.log 2>&1 || { echo "ERROR: could not run mosaics-v2.py p05" >> log_3_v2_p05.log; exit 1; }

echo "Running main script v2 with high penalty..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic-v2.py -folder /mnt/ebs/samples -penalty 0.15 -suffix _p15_v2 > log_3_v2_p15.log 2>&1 || { echo "ERROR: could not run mosaics-v2.py p15" >> log_3_v2_p15.log; exit 1; }

echo "Uploading results!" >> pipeline_status.log
$VENV_PYTHON - u tools/load_data_from_s3 --upload-reulst > log_4_upload.log 2>&1 || { echo "ERROR: could not upload results " >> log_3_v2_p15.log; exit 1; }
echo "=== Pipeline Finished Successfully at $(date) ===" >> pipeline_status.log