from pathlib import Path

from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import Session, declarative_base

from fastapi_storages import FileSystemStorage, StorageFile, StorageImage
from fastapi_storages.integrations.sqlalchemy import FileType
from tests.engine import database_uri
from tests.test_integrations.utils import UploadFile


def test_filesystem_storage_file_properties(tmp_path: Path) -> None:
    tmp_file = tmp_path / "example.txt"
    tmp_file.write_bytes(b"123")

    storage = FileSystemStorage(path=tmp_path)
    file = StorageFile(name="example.txt", storage=storage)

    assert file.name == "example.txt"
    assert file.size == 3
    assert file.path == str(tmp_file)
    assert str(file).endswith(file.name)


def test_filesystem_storage_image_properties(tmp_path: Path) -> None:
    tmp_file = tmp_path / "example.txt"
    tmp_file.write_bytes(b"123")

    storage = FileSystemStorage(path=tmp_path)
    image = StorageImage(name="example.txt", storage=storage, height=1, width=1)

    assert image.height == 1
    assert image.width == 1


def test_filesystem_storage_file_read_write(tmp_path: Path) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"123")

    storage = FileSystemStorage(path=tmp_path)
    file = StorageFile(name="example.txt", storage=storage)
    file.write(file=input_file.open("rb"))

    byte_data = file.open().read()

    assert byte_data == b"123"


def test_filesystem_storage_rename_file_names(tmp_path: Path) -> None:
    tmp_file = tmp_path / "input.txt"
    tmp_file.touch()

    class NonOverwritingFileSystemStorage(FileSystemStorage):
        OVERWRITE_EXISTING_FILES = False

    storage = NonOverwritingFileSystemStorage(path=tmp_path)
    file1 = StorageFile(name="duplicate.txt", storage=storage)
    file1.write(file=tmp_file.open("rb"))

    file2 = StorageFile(name="duplicate.txt", storage=storage)
    file2.write(file=tmp_file.open("rb"))

    file3 = StorageFile(name="duplicate.txt", storage=storage)
    file3.write(file=tmp_file.open("rb"))

    assert file1.name == "duplicate.txt"
    assert file2.name == "duplicate_1.txt"
    assert file3.name == "duplicate_2.txt"

    assert Path(file1.path) == tmp_path / "duplicate.txt"
    assert Path(file2.path) == tmp_path / "duplicate_1.txt"
    assert Path(file3.path) == tmp_path / "duplicate_2.txt"


def test_filesystem_storage_path_traversal_blocked(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    storage = FileSystemStorage(path=str(storage_root))

    assert storage.get_name("../../etc/passwd") == "etc/passwd"
    assert storage.get_name("/etc/passwd") == "etc/passwd"
    assert storage.get_name("../secret.txt") == "secret.txt"


def test_filesystem_storage_path_traversal_write_contained(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    storage = FileSystemStorage(path=str(storage_root))
    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"123")

    file = StorageFile(name="../../escape.txt", storage=storage)
    file.write(file=input_file.open("rb"))

    written = Path(file.path)
    assert written.is_relative_to(storage_root)
    assert not (tmp_path / "escape.txt").exists()


def test_filesystem_storage_path_traversal_upload_to_callable(tmp_path: Path) -> None:
    Base = declarative_base()
    engine = create_engine(database_uri)
    storage_root = tmp_path / "storage"

    class M(Base):
        __tablename__ = "traversal_model"
        id = Column(Integer, primary_key=True)
        file = Column(
            FileType(
                storage=FileSystemStorage(path=str(storage_root)),
                upload_to=lambda name: f"../../evil/{name}",
            )
        )

    Base.metadata.create_all(engine)
    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"123")

    upload_file = UploadFile(file=input_file.open("rb"), filename="pwn.txt")
    model = M(file=upload_file)

    with Session(engine) as session:
        session.add(model)
        session.commit()
        written = Path(storage_root / model.file.name)
        assert written.is_relative_to(storage_root)
        assert not (tmp_path / "evil").exists()

    Base.metadata.drop_all(engine)


def test_filesystem_storage_rename_preserves_prefix(tmp_path: Path) -> None:
    class NonOverwritingStorage(FileSystemStorage):
        OVERWRITE_EXISTING_FILES = False

    storage = NonOverwritingStorage(path=str(tmp_path))
    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"123")

    file1 = StorageFile(name="uploads/photo.jpg", storage=storage)
    file1.write(file=input_file.open("rb"))

    file2 = StorageFile(name="uploads/photo.jpg", storage=storage)
    file2.write(file=input_file.open("rb"))

    file3 = StorageFile(name="uploads/photo.jpg", storage=storage)
    file3.write(file=input_file.open("rb"))

    assert file1.name == "uploads/photo.jpg"
    assert file2.name == "uploads/photo_1.jpg"
    assert file3.name == "uploads/photo_2.jpg"
    assert Path(file2.path) == tmp_path / "uploads" / "photo_1.jpg"
    assert Path(file3.path) == tmp_path / "uploads" / "photo_2.jpg"


def test_filesystem_storage_delete_file(tmp_path: Path) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"123")

    storage = FileSystemStorage(path=tmp_path)
    file = StorageFile(name="example.txt", storage=storage)
    file.write(file=input_file.open("rb"))

    assert (tmp_path / "example.txt").exists() is True

    file.delete()

    assert (tmp_path / "example.txt").exists() is False
