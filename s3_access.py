import boto3
import os
from botocore.exceptions import ClientError


class S3Access:
    """S3 access class for managing S3 bucket operations."""

    def __init__(self, bucket_name):
        """
        Initialize S3Access with a bucket name.

        @Args:
            bucket_name (str): Name of the S3 bucket to connect to
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')

    def list_sources(self):
        """
        List all objects in the sources folder of the S3 bucket.

        Returns:
            list: List of object keys in the sources folder
        """
        try:
            # List objects with prefix 'sources/'
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='sources/'
            )

            # Extract object keys from the response
            if 'Contents' in response:
                object_keys = [obj['Key'] for obj in response['Contents']]
                return object_keys
            else:
                return []

        except ClientError as e:
            print(f"Error listing sources: {e}")
            return []

    def rename_key(self, current_key, new_key):
        """
        Rename an S3 object by copying it to a new key and deleting the old.

        Args:
            current_key (str): Current key name of the S3 object
            new_key (str): New key name for the S3 object

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Copy the object to the new key
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': current_key
            }

            self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource=copy_source,
                Key=new_key
            )

            # Delete the original object
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=current_key
            )

            print(f"Successfully renamed {current_key} to {new_key}")
            return True

        except ClientError as e:
            print(f"Error renaming key {current_key} to {new_key}: {e}")
            return False

    def put_object(self, key, file_object):
        """
        Upload a file object to S3 with the specified key.

        Args:
            key (str): Key name for the S3 object
            file_object: File-like object to upload (must support read())

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_object
            )

            print(f"Successfully uploaded object to {key}")
            return True

        except ClientError as e:
            print(f"Error uploading object to {key}: {e}")
            return False

    def get_object(self, key):
        """
        Get an object from S3 with the specified key.

        Args:
            key (str): Key name of the S3 object to retrieve

        Returns:
            bytes: File content as bytes, or None if error
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            file_content = response['Body'].read()
            print(f"Successfully retrieved object {key}")
            return file_content

        except ClientError as e:
            print(f"Error retrieving object {key}: {e}")
            return None

    def object_exists(self, key):
        """
        Check if an object exists in S3 with the specified key.

        Args:
            key (str): Key name of the S3 object to check

        Returns:
            bool: True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                print(f"Error checking if object {key} exists: {e}")
                return False

    def delete_object(self, key):
        """
        Delete an object from S3 with the specified key.

        Args:
            key (str): Key name of the S3 object to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )

            print(f"Successfully deleted object {key}")
            return True

        except ClientError as e:
            print(f"Error deleting object {key}: {e}")
            return False

    def download_to_disk(self, s3_key, local_path):
        """
        Downloads a file from S3 directly to the local filesystem.

        Args:
            s3_key (str): The key of the object in S3.
            local_path (str): Where to save the file locally.
        """
        try:
            # Create the local directory if it doesn't exist
            local_dir = os.path.dirname(local_path)
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir)

            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            print(f"Successfully downloaded {s3_key} to {local_path}")
            return True
        except ClientError as e:
            print(f"Error downloading {s3_key}: {e}")
            return False

    def upload_from_disk(self, local_path, s3_key):
        """
        Uploads a file from the local filesystem to S3.

        Args:
            local_path (str): Path to the local file.
            s3_key (str): The destination key in S3.
        """
        if not os.path.isfile(local_path):
            print(f"Error: Local file {local_path} does not exist.")
            return False

        try:
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            print(f"Successfully uploaded {local_path} to {s3_key}")
            return True
        except ClientError as e:
            print(f"Error uploading {local_path}: {e}")
            return False
