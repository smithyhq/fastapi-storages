import io
from pathlib import Path

import pytest
from peewee import AutoField, Model, SqliteDatabase
from PIL import Image

from fastapi_storages import FileSystemStorage
from fastapi_storages.exceptions import ValidationException
from fastapi_storages.integrations.peewee import ImageType
from tests.engine import database_name
from tests.test_integrations.utils import UploadFile

db = SqliteDatabase(database_name)


class ModelTest(Model):
    id = AutoField(primary_key=True)
    image = ImageType(storage=FileSystemStorage(path="/tmp"), null=True)

    class Meta:
        database = db


@pytest.fixture(autouse=True)
def prepare_database():
    db.create_tables([ModelTest])
    yield
    db.drop_tables([ModelTest])


def test_valid_image(tmp_path: Path) -> None:
    ModelTest.image.storage = FileSystemStorage(path=str(tmp_path))

    input_file = tmp_path / "input.png"
    image = Image.new("RGB", (800, 1280), (255, 255, 255))
    image.save(input_file, "PNG")

    upload_file = UploadFile(file=input_file.open("rb"), filename="image.png")
    ModelTest.create(image=upload_file)
    model = ModelTest.get()

    assert model.image.name == "image.png"
    assert model.image.size == input_file.stat().st_size
    assert model.image.path == str(tmp_path / "image.png")


def test_invalid_image(tmp_path: Path) -> None:
    input_file = tmp_path / "image.png"
    input_file.write_bytes(b"123")
    upload_file = UploadFile(file=input_file.open("rb"), filename="image.png")

    with pytest.raises(ValidationException):
        ModelTest.create(image=upload_file)


def test_nullable_image() -> None:
    ModelTest.create(image=None)
    model = ModelTest.get()

    assert model.image is None


def test_clear_empty_image() -> None:
    upload_file = UploadFile(file=io.BytesIO(b""), filename="")
    ModelTest.create(image=upload_file)
    model = ModelTest.get()

    assert model.image is None
