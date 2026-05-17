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


def test_valid_image(tmp_path: Path) -> None:
    storage = FileSystemStorage(path=str(tmp_path))
    Base = declarative_base()
    engine = create_engine(database_uri)

    class Model(Base):
        __tablename__ = "model"
        id = Column(Integer, primary_key=True)
        image = Column(ImageType(storage=storage))

    Base.metadata.create_all(engine)

    input_file = tmp_path / "input.png"
    Image.new("RGB", (800, 1280), (255, 255, 255)).save(input_file, "PNG")
    model = Model(image=UploadFile(file=input_file.open("rb"), filename="image.png"))

    with Session(engine) as session:
        session.add(model)
        session.commit()
        assert model.image.name == "image.png"
        assert model.image.size == input_file.stat().st_size
        assert model.image.path == str(tmp_path / "image.png")

    Base.metadata.drop_all(engine)


def test_invalid_image(tmp_path: Path) -> None:
    storage = FileSystemStorage(path=str(tmp_path))
    Base = declarative_base()
    engine = create_engine(database_uri)

    class Model(Base):
        __tablename__ = "model"
        id = Column(Integer, primary_key=True)
        image = Column(ImageType(storage=storage))

    Base.metadata.create_all(engine)

    input_file = tmp_path / "image.png"
    input_file.write_bytes(b"123")
    model = Model(image=UploadFile(file=input_file.open("rb"), filename="image.png"))

    with Session(engine) as session:
        session.add(model)
        with pytest.raises(StatementError):
            session.commit()

    Base.metadata.drop_all(engine)
