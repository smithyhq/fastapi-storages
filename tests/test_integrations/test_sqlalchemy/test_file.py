import io
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import Session, declarative_base

from fastapi_storages import FileSystemStorage
from fastapi_storages.integrations.sqlalchemy import FileType
from tests.engine import database_uri
from tests.test_integrations.utils import UploadFile

Base = declarative_base()
engine = create_engine(database_uri)


class Model(Base):
    __tablename__ = "model"

    id = Column(Integer, primary_key=True)
    file = Column(FileType(storage=FileSystemStorage(path="/tmp")))


@pytest.fixture(autouse=True)
def prepare_database():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_valid_file(tmp_path: Path) -> None:
    Model.file.type.storage = FileSystemStorage(path=str(tmp_path))

    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"123")

    upload_file = UploadFile(file=input_file.open("rb"), filename="example.txt")
    model = Model(file=upload_file)

    with Session(engine) as session:
        session.add(model)
        session.commit()

        assert model.file.name == "example.txt"
        assert model.file.size == 3
        assert model.file.path == str(tmp_path / "example.txt")


def test_nullable_file() -> None:
    model = Model(file=None)

    with Session(engine) as session:
        session.add(model)
        session.commit()

        assert model.file is None


def test_clear_empty_file() -> None:
    upload_file = UploadFile(file=io.BytesIO(b""), filename="")
    model = Model(file=upload_file)

    with Session(engine) as session:
        session.add(model)
        session.commit()

        assert model.file is None


def test_filter_by_string_value(tmp_path: Path) -> None:
    Model.file.type.storage = FileSystemStorage(path=str(tmp_path))

    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"123")

    upload_file = UploadFile(file=input_file.open("rb"), filename="photo.jpg")
    model = Model(file=upload_file)

    with Session(engine) as session:
        session.add(model)
        session.commit()

        result = session.query(Model).filter(Model.file.endswith(".jpg")).first()
        assert result is not None
        assert result.file.name == "photo.jpg"
