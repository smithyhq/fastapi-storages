import mimetypes
import os
from pathlib import Path
from typing import BinaryIO

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None

from fastapi_storages.base import BaseStorage
from fastapi_storages.utils import secure_filename


class S3Storage(BaseStorage):
    """
    Amazon S3 or any S3 compatible storage backend.
    You might want to use this with the `FileType` type.
    Requires `boto3` to be installed.
    """

    default_content_type = "application/octet-stream"

    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
    """AWS access key ID. Either set here or as an environment variable."""

    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    """AWS secret access key. Either set here or as an environment variable."""

    AWS_S3_BUCKET_NAME = ""
    """AWS S3 bucket name to use."""

    AWS_S3_ENDPOINT_URL = ""
    """AWS S3 endpoint URL."""

    AWS_S3_USE_SSL = True
    """Indicate if SSL should be used."""

    AWS_DEFAULT_ACL = ""
    """Optional ACL set on the object like `public-read`.
    By default file will be private."""

    AWS_QUERYSTRING_AUTH = False
    """Indicate if query parameter authentication should be used in URLs."""

    AWS_S3_CUSTOM_DOMAIN = ""
    """Custom domain to use for serving object URLs."""

    def __init__(self) -> None:
        assert boto3 is not None, "'boto3' is not installed"
        assert not self.AWS_S3_ENDPOINT_URL.startswith("http"), (
            "URL should not contain protocol"
        )

        self._http_scheme = "https" if self.AWS_S3_USE_SSL else "http"
        self._url = f"{self._http_scheme}://{self.AWS_S3_ENDPOINT_URL}"
        self._s3 = boto3.client(
            "s3",
            endpoint_url=self._url,
            use_ssl=self.AWS_S3_USE_SSL,
            aws_access_key_id=self.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
        )

    def get_name(self, name: str) -> str:
        """
        Get the normalized name of the file.
        """

        filename = secure_filename(Path(name).name)
        return str(Path(name).with_name(filename))

    def get_path(self, name: str) -> str:
        """
        Get full URL to the file.
        """

        key = self.get_name(name)

        if self.AWS_S3_CUSTOM_DOMAIN:
            return "{}://{}/{}".format(
                self._http_scheme,
                self.AWS_S3_CUSTOM_DOMAIN,
                key,
            )

        if self.AWS_QUERYSTRING_AUTH:
            params = {"Bucket": self.AWS_S3_BUCKET_NAME, "Key": key}
            return self._s3.generate_presigned_url("get_object", Params=params)

        return "{}://{}/{}/{}".format(
            self._http_scheme,
            self.AWS_S3_ENDPOINT_URL,
            self.AWS_S3_BUCKET_NAME,
            key,
        )

    def get_size(self, name: str) -> int:
        """
        Get file size in bytes.
        """

        key = self.get_name(name)
        return self._s3.head_object(Bucket=self.AWS_S3_BUCKET_NAME, Key=key)[
            "ContentLength"
        ]

    def write(self, file: BinaryIO, name: str) -> str:
        """
        Write input file which is opened in binary mode to destination.
        """

        file.seek(0, 0)
        key = self.get_name(name)
        content_type, _ = mimetypes.guess_type(key)
        params = {
            "ACL": self.AWS_DEFAULT_ACL,
            "ContentType": content_type or self.default_content_type,
        }
        self._s3.upload_fileobj(file, self.AWS_S3_BUCKET_NAME, key, ExtraArgs=params)
        return key

    def delete(self, name: str) -> None:
        """
        Delete the file from S3
        """

        self._s3.delete_object(Bucket=self.AWS_S3_BUCKET_NAME, Key=self.get_name(name))

    def generate_new_filename(self, filename: str) -> str:
        key = self.get_name(filename)
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 0

        while self._check_object_exists(key):
            counter += 1
            filename = f"{stem}_{counter}{suffix}"
            key = self.get_name(filename)

        return filename

    def _check_object_exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self.AWS_S3_BUCKET_NAME, Key=key)
        except boto3.exceptions.botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False

        return True
