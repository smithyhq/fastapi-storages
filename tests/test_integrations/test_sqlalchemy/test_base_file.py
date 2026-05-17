import io
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import Session, declarative_base

from fastapi_storages import FileSystemStorage
from fastapi_storages.integrations.sqlalchemy import FileType, ImageType
from tests.engine import database_uri
from tests.test_integrations.utils import UploadFile


class NonOverwritingStorage(FileSystemStorage):
    OVERWRITE_EXISTING_FILES = False


@pytest.fixture(params=[FileType, ImageType], ids=["FileType", "ImageType"])
def model(request, tmp_path):
    ColumnType = request.param
    storage = FileSystemStorage(path=str(tmp_path))
    Base = declarative_base()
    engine = create_engine(database_uri)

    class M(Base):
        __tablename__ = "model"
        id = Column(Integer, primary_key=True)
        field = Column(ColumnType(storage=storage))

    Base.metadata.create_all(engine)
    yield M, engine
    Base.metadata.drop_all(engine)


@pytest.fixture(params=[FileType, ImageType], ids=["FileType", "ImageType"])
def typed_upload(request, tmp_path):
    ColumnType = request.param
    if ColumnType is FileType:
        src = tmp_path / "_src.bin"
        src.write_bytes(b"hello")
        filename = "photo.jpg"
    else:
        src = tmp_path / "_src.png"
        Image.new("RGB", (10, 10)).save(src, "PNG")
        filename = "photo.png"
    yield ColumnType, src, filename, tmp_path


def test_nullable(model) -> None:
    M, engine = model
    m = M(field=None)

    with Session(engine) as session:
        session.add(m)
        session.commit()
        assert m.field is None


def test_clear_empty(model) -> None:
    M, engine = model
    m = M(field=UploadFile(file=io.BytesIO(b""), filename=""))

    with Session(engine) as session:
        session.add(m)
        session.commit()
        assert m.field is None


def test_upload_to_string_prefix(typed_upload) -> None:
    ColumnType, src, filename, tmp_path = typed_upload
    storage = FileSystemStorage(path=str(tmp_path))
    Base = declarative_base()
    engine = create_engine(database_uri)

    class M(Base):
        __tablename__ = "model"
        id = Column(Integer, primary_key=True)
        field = Column(ColumnType(storage=storage, upload_to="uploads"))

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        m = M(field=UploadFile(file=src.open("rb"), filename=filename))
        session.add(m)
        session.commit()
        assert m.field.name == f"uploads/{filename}"

    Base.metadata.drop_all(engine)


def test_upload_to_callable(typed_upload) -> None:
    ColumnType, src, filename, tmp_path = typed_upload
    storage = FileSystemStorage(path=str(tmp_path))
    Base = declarative_base()
    engine = create_engine(database_uri)

    class M(Base):
        __tablename__ = "model"
        id = Column(Integer, primary_key=True)
        field = Column(ColumnType(storage=storage, upload_to=lambda n: f"users/42/{n}"))

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        m = M(field=UploadFile(file=src.open("rb"), filename=filename))
        session.add(m)
        session.commit()
        assert m.field.name == f"users/42/{filename}"

    Base.metadata.drop_all(engine)


def test_upload_to_trailing_slash(typed_upload) -> None:
    ColumnType, src, filename, tmp_path = typed_upload
    storage = FileSystemStorage(path=str(tmp_path))
    Base = declarative_base()
    engine = create_engine(database_uri)

    class M(Base):
        __tablename__ = "model"
        id = Column(Integer, primary_key=True)
        field = Column(ColumnType(storage=storage, upload_to="uploads/"))

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        m = M(field=UploadFile(file=src.open("rb"), filename=filename))
        session.add(m)
        session.commit()
        assert m.field.name == f"uploads/{filename}"

    Base.metadata.drop_all(engine)


def test_upload_to_with_overwrite_protection(typed_upload) -> None:
    ColumnType, src, filename, tmp_path = typed_upload
    storage = NonOverwritingStorage(path=str(tmp_path))
    Base = declarative_base()
    engine = create_engine(database_uri)

    class M(Base):
        __tablename__ = "model"
        id = Column(Integer, primary_key=True)
        field = Column(ColumnType(storage=storage, upload_to="uploads"))

    Base.metadata.create_all(engine)

    stem = Path(filename).stem
    ext = Path(filename).suffix

    with Session(engine) as session:
        m1 = M(field=UploadFile(file=src.open("rb"), filename=filename))
        session.add(m1)
        session.commit()
        session.refresh(m1)
        assert m1.field.name == f"uploads/{filename}"

    with Session(engine) as session:
        m2 = M(field=UploadFile(file=src.open("rb"), filename=filename))
        session.add(m2)
        session.commit()
        session.refresh(m2)
        assert m2.field.name == f"uploads/{stem}_1{ext}"

    Base.metadata.drop_all(engine)
