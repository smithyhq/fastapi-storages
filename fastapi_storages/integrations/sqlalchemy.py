from abc import abstractmethod
from typing import Any, Callable

from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, Unicode

try:
    from PIL import Image, UnidentifiedImageError

    PIL = True
except ImportError:  # pragma: no cover
    PIL = False

from fastapi_storages.base import BaseStorage, StorageFile, StorageImage
from fastapi_storages.exceptions import ValidationException


class BaseFileType(TypeDecorator):
    impl = Unicode
    cache_ok = True

    def __init__(
        self,
        storage: BaseStorage,
        upload_to: str | Callable[[str], str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.storage = storage
        self.upload_to = upload_to
        super().__init__(*args, **kwargs)

    def _get_path(self, filename: str) -> str:
        if self.upload_to is None:
            return filename
        if callable(self.upload_to):
            return self.upload_to(filename)
        return f"{self.upload_to.rstrip('/')}/{filename}"

    @abstractmethod
    def save(self, value: Any) -> str: ...

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return value
        if isinstance(value, str):
            return value
        if len(value.file.read(1)) != 1:
            value.file.seek(0)
            return None
        return self.save(value)


class FileType(BaseFileType):
    """
    File type to be used with Storage classes. Stores the file name in the column.

    ???+ usage
        ```python
        from fastapi_storages import FileSystemStorage
        from fastapi_storages.integrations.sqlalchemy import FileType

        class Example(Base):
            __tablename__ = "example"

            id = Column(Integer, primary_key=True)
            file = Column(FileType(storage=FileSystemStorage(path="/tmp")))
        ```
    """

    cache_ok = True

    def save(self, value: Any) -> str:
        file = StorageFile(name=self._get_path(value.filename), storage=self.storage)
        file.write(file=value.file)
        value.file.close()
        return file.name

    def process_result_value(self, value: Any, dialect: Dialect) -> StorageFile | None:
        if value is None:
            return value
        return StorageFile(name=value, storage=self.storage)


class ImageType(BaseFileType):
    """
    Image type using `PIL` package to be used with Storage classes.
    Stores the image path in the column.

    ???+ usage
        ```python
        from fastapi_storages import FileSystemStorage
        from fastapi_storages.integrations.sqlalchemy import ImageType

        class Example(Base):
            __tablename__ = "example"

            id = Column(Integer, primary_key=True)
            image = Column(ImageType(storage=FileSystemStorage(path="/tmp")))
        ```
    """

    cache_ok = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        assert PIL is True, "'Pillow' package is required."
        super().__init__(*args, **kwargs)

    def save(self, value: Any) -> str:
        try:
            with Image.open(value.file) as image_file:
                image_file.verify()
                height, width = image_file.height, image_file.width
        except UnidentifiedImageError:
            raise ValidationException("Invalid image file")

        image = StorageImage(
            name=self._get_path(value.filename),
            storage=self.storage,
            height=height,
            width=width,
        )
        image.write(file=value.file)
        value.file.close()
        return image.name

    def process_result_value(self, value: Any, dialect: Dialect) -> StorageImage | None:
        if value is None:
            return value
        with Image.open(self.storage.get_path(value)) as image:
            return StorageImage(
                name=value, storage=self.storage, height=image.height, width=image.width
            )
