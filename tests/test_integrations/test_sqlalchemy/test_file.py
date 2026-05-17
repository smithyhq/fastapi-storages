from pathlib import Path

from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import Session, declarative_base

from fastapi_storages import FileSystemStorage
from fastapi_storages.integrations.sqlalchemy import FileType
from tests.engine import database_uri
from tests.test_integrations.utils import UploadFile


def test_valid_file(tmp_path: Path) -> None:
    storage = FileSystemStorage(path=str(tmp_path))
    Base = declarative_base()
    engine = create_engine(database_uri)

    class Model(Base):
        __tablename__ = "model"
        id = Column(Integer, primary_key=True)
        file = Column(FileType(storage=storage))

    Base.metadata.create_all(engine)

    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"123")
    model = Model(file=UploadFile(file=input_file.open("rb"), filename="example.txt"))

    with Session(engine) as session:
        session.add(model)
        session.commit()
        assert model.file.name == "example.txt"
        assert model.file.size == 3
        assert model.file.path == str(tmp_path / "example.txt")

    Base.metadata.drop_all(engine)


def test_filter_by_string_value(tmp_path: Path) -> None:
    storage = FileSystemStorage(path=str(tmp_path))
    Base = declarative_base()
    engine = create_engine(database_uri)

    class Model(Base):
        __tablename__ = "model"
        id = Column(Integer, primary_key=True)
        file = Column(FileType(storage=storage))

    Base.metadata.create_all(engine)

    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"123")
    model = Model(file=UploadFile(file=input_file.open("rb"), filename="photo.jpg"))

    with Session(engine) as session:
        session.add(model)
        session.commit()
        result = session.query(Model).filter(Model.file.endswith(".jpg")).first()
        assert result is not None
        assert result.file.name == "photo.jpg"

    Base.metadata.drop_all(engine)
