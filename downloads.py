##################################################
# This script is intend to be run locally to get
# resulting images from s3.
###################################################

import boto3
import os
import argparse


def download_s3_folder(bucket_name, prefix, local_dir, region):
    s3 = boto3.client('s3', region_name=region)

    paginator = s3.get_paginator('list_objects_v2')
    params = {'Bucket': bucket_name, 'Prefix': prefix}

    os.makedirs(local_dir, exist_ok=True)

    for page in paginator.paginate(**params):
        if 'Contents' not in page:
            print("No files found with the given prefix.")
            return
        for obj in page['Contents']:
            key = obj['Key']
            if key.endswith('/'):
                # Skip folders
                continue

            # Create the full local path
            relative_path = os.path.relpath(key, prefix)
            local_file_path = os.path.join(local_dir, relative_path)
            local_file_dir = os.path.dirname(local_file_path)
            os.makedirs(local_file_dir, exist_ok=True)

            print(f"Downloading {key} to {local_file_path}")
            s3.download_file(bucket_name, key, local_file_path)


def main():
    parser = argparse.ArgumentParser(description='Download S3 \
                                     files to local directory.')
    parser.add_argument('--bucket',
                        required=True, help='Name of the S3 bucket.')
    parser.add_argument('--region',
                        default='us-west-2',
                        help='AWS region of the S3 bucket. Default: us-west-2')
    parser.add_argument('--prefix', required=True,
                        help='Prefix (folder) in S3 to download.')

    args = parser.parse_args()

    download_s3_folder(args.bucket, args.prefix, 'test-results', args.region)


if __name__ == "__main__":
    main()
