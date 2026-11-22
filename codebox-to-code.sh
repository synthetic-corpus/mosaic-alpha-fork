#!/bin/bash

export S3_STORAGE="replace-with-bucket"

# Explicitly use the python binary inside your virtual environment to ensure stability
VENV_PYTHON=".venv/bin/python3"

echo "=== Starting Codebox Test at $(date) ===" > pipeline_status.log

# 3. Codebox comparisons
echo "Running original codebox mosaic.py..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic.py -folder /mnt/ebs/samples -suffix _legacy > log_2_legacy.log 2>&1 || { echo "ERROR: could not run mosaic.py legacy" >> log_2_legacy.log; exit 1; }

echo "Running mosaic-codebox.py with penalty 0.0..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic-codebox.py -folder /mnt/ebs/samples -penalty 0.0 -suffix _p00_codebox > log_3_codebox_p00.log 2>&1 || { echo "ERROR: could not run mosaic-codebox.py p00" >> log_3_codebox_p00.log; exit 1; }

echo "Running mosaic-codebox.py with penalty 0.03..." >> pipeline_status.log
$VENV_PYTHON -u mosaicizers/mosaic-codebox.py -folder /mnt/ebs/samples -penalty 0.03 -suffix _p03_codebox > log_3_codebox_p03.log 2>&1 || { echo "ERROR: could not run mosaic-codebox.py p03" >> log_3_codebox_p03.log; exit 1; }

echo "Uploading results!" >> pipeline_status.log
$VENV_PYTHON -u tools/load_data_from_s3.py --upload-results > log_4_upload.log 2>&1 || { echo "ERROR: could not upload results" >> log_4_upload.log; exit 1; }
echo "=== Codebox Test Finished Successfully at $(date) ===" >> pipeline_status.log
