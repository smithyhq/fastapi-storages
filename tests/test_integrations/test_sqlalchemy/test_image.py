import io
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session, declarative_base

from fastapi_storages import FileSystemStorage
from fastapi_storages.integrations.sqlalchemy import ImageType
from tests.engine import database_uri
from tests.test_integrations.utils import UploadFile

Base = declarative_base()
engine = create_engine(database_uri)


class Model(Base):
    __tablename__ = "model"

    id = Column(Integer, primary_key=True)
    image = Column(ImageType(storage=FileSystemStorage(path="/tmp")))


@pytest.fixture(autouse=True)
def prepare_database():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_valid_image(tmp_path: Path) -> None:
    Model.image.type.storage = FileSystemStorage(path=str(tmp_path))

    input_file = tmp_path / "input.png"
    image = Image.new("RGB", (800, 1280), (255, 255, 255))
    image.save(input_file, "PNG")

    upload_file = UploadFile(file=input_file.open("rb"), filename="image.png")
    model = Model(image=upload_file)

    with Session(engine) as session:
        session.add(model)
        session.commit()

        assert model.image.name == "image.png"
        assert model.image.size == input_file.stat().st_size
        assert model.image.path == str(tmp_path / "image.png")


def test_invalid_image(tmp_path: Path) -> None:
    input_file = tmp_path / "image.png"
    input_file.write_bytes(b"123")

    upload_file = UploadFile(file=input_file.open("rb"), filename="image.png")
    model = Model(image=upload_file)

    with Session(engine) as session:
        session.add(model)

        with pytest.raises(StatementError):
            session.commit()


def test_nullable_image() -> None:
    model = Model(image=None)

    with Session(engine) as session:
        session.add(model)
        session.commit()

        assert model.image is None


def test_clear_empty_image() -> None:
    upload_file = UploadFile(file=io.BytesIO(b""), filename="")
    model = Model(image=upload_file)

    with Session(engine) as session:
        session.add(model)
        session.commit()

        assert model.image is None
