import os
from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from fastapi_storages import S3Storage, StorageFile

os.environ["MOTO_S3_CUSTOM_ENDPOINTS"] = "http://custom.s3.endpoint"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


class PrivateS3Storage(S3Storage):
    AWS_ACCESS_KEY_ID = "access"
    AWS_SECRET_ACCESS_KEY = "secret"
    AWS_S3_BUCKET_NAME = "bucket"
    AWS_S3_ENDPOINT_URL = "custom.s3.endpoint"
    AWS_S3_USE_SSL = False
    AWS_S3_SIGNATURE_VERSION = "s3v4"


@mock_aws
def test_s3_storage_methods(tmp_path: Path) -> None:
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="bucket")

    tmp_file = tmp_path / "example.txt"
    tmp_file.write_bytes(b"123")

    storage = PrivateS3Storage()

    assert storage.get_name("test (1).txt") == "test_1.txt"
    assert (
        storage.get_path("test (1).txt")
        == "http://custom.s3.endpoint/bucket/test_1.txt"
    )
    assert (
        storage.get_path("a/test.txt") == "http://custom.s3.endpoint/bucket/a/test.txt"
    )
    assert (
        storage.get_path("a/b/c/test.txt")
        == "http://custom.s3.endpoint/bucket/a/b/c/test.txt"
    )

    storage.write(tmp_file.open("rb"), "example.txt")
    assert storage.get_size("example.txt") == 3


@mock_aws
def test_s3_storage_querystring_auth(tmp_path: Path) -> None:
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="bucket")

    tmp_file = tmp_path / "example.txt"
    tmp_file.write_bytes(b"123")

    class TestStorage(PrivateS3Storage):
        AWS_QUERYSTRING_AUTH = True

    storage = TestStorage()

    assert storage.get_path("test.txt").startswith(
        "http://custom.s3.endpoint/bucket/test.txt?"
    )
    assert storage.get_path("test.txt").count("X-Amz-Credential=access") == 1
    assert storage.get_path("test.txt").count("X-Amz-Signature=") == 1
    assert storage.get_path("test.txt").count("X-Amz-Expires=") == 1


@mock_aws
def test_s3_storage_custom_domain(tmp_path: Path) -> None:
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="bucket")

    tmp_file = tmp_path / "example.txt"
    tmp_file.write_bytes(b"123")

    class TestStorage(PrivateS3Storage):
        AWS_S3_CUSTOM_DOMAIN = "s3.fastapi.storages"

    storage = TestStorage()

    assert storage.get_path("test.txt") == "http://s3.fastapi.storages/test.txt"


@mock_aws
def test_s3_storage_rename_file_names(tmp_path: Path) -> None:
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="bucket")

    tmp_file = tmp_path / "input.txt"
    tmp_file.write_bytes(b"123")

    class TestStorage(PrivateS3Storage):
        AWS_S3_CUSTOM_DOMAIN = "s3.fastapi.storages"
        OVERWRITE_EXISTING_FILES = False

    storage = TestStorage()

    file1 = StorageFile(name="duplicate.txt", storage=storage)
    file1.write(file=tmp_file.open("rb"))

    file2 = StorageFile(name="duplicate.txt", storage=storage)
    file2.write(file=tmp_file.open("rb"))

    file3 = StorageFile(name="duplicate.txt", storage=storage)
    file3.write(file=tmp_file.open("rb"))

    assert file1.name == "duplicate.txt"
    assert file2.name == "duplicate_1.txt"
    assert file3.name == "duplicate_2.txt"

    assert file1.path == "http://s3.fastapi.storages/duplicate.txt"
    assert file2.path == "http://s3.fastapi.storages/duplicate_1.txt"
    assert file3.path == "http://s3.fastapi.storages/duplicate_2.txt"


@mock_aws
def test_s3_storage_delete_file(tmp_path: Path) -> None:
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="bucket")

    tmp_file = tmp_path / "example.txt"
    tmp_file.write_bytes(b"123")

    storage = PrivateS3Storage()

    file = StorageFile(name="file.txt", storage=storage)
    file.write(file=tmp_file.open("rb"))

    assert s3.head_object(Bucket="bucket", Key="file.txt")

    file.delete()

    with pytest.raises(ClientError):
        s3.head_object(Bucket="bucket", Key="file.txt")


@mock_aws
def test_s3_storage_from_env(monkeypatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("AWS_S3_BUCKET_NAME", "bucket")
    monkeypatch.setenv("AWS_S3_ENDPOINT_URL", "custom.s3.endpoint")
    monkeypatch.setenv("AWS_S3_USE_SSL", "false")
    monkeypatch.setenv("AWS_DEFAULT_ACL", "public-read")
    monkeypatch.setenv("AWS_QUERYSTRING_AUTH", "false")
    monkeypatch.setenv("AWS_S3_CUSTOM_DOMAIN", "")
    monkeypatch.setenv("AWS_S3_SIGNATURE_VERSION", "s3v4")

    # Reload so class-level lookup_env calls pick up monkeypatched env
    import importlib
    import fastapi_storages.s3 as s3_module

    importlib.reload(s3_module)

    boto3.client("s3").create_bucket(Bucket="bucket")

    storage = s3_module.S3Storage()
    assert storage.AWS_S3_BUCKET_NAME == "bucket"
    assert storage.AWS_S3_ENDPOINT_URL == "custom.s3.endpoint"
    assert storage.AWS_S3_USE_SSL is False
    assert storage.AWS_DEFAULT_ACL == "public-read"
    assert storage.AWS_S3_SIGNATURE_VERSION == "s3v4"
    assert storage.get_path("test.txt") == "http://custom.s3.endpoint/bucket/test.txt"
