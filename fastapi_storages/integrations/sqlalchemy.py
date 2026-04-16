from typing import Any, Optional

from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, Unicode

try:
    from PIL import Image, UnidentifiedImageError

    PIL = True
except ImportError:  # pragma: no cover
    PIL = False

from fastapi_storages.base import BaseStorage, StorageFile, StorageImage
from fastapi_storages.exceptions import ValidationException


class FileType(TypeDecorator):
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

    impl = Unicode
    cache_ok = True

    def __init__(self, storage: BaseStorage, *args: Any, **kwargs: Any) -> None:
        self.storage = storage
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: Any, dialect: Dialect) -> Optional[str]:
        if value is None:
            return value
        if len(value.file.read(1)) != 1:
            value.file.seek(0)
            return None

        file = StorageFile(name=value.filename, storage=self.storage)
        file.write(file=value.file)

        value.file.close()
        return file.name

    def process_result_value(
        self, value: Any, dialect: Dialect
    ) -> Optional[StorageFile]:
        if value is None:
            return value

        return StorageFile(name=value, storage=self.storage)


class ImageType(TypeDecorator):
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

    impl = Unicode
    cache_ok = True

    def __init__(self, storage: BaseStorage, *args: Any, **kwargs: Any) -> None:
        assert PIL is True, "'Pillow' package is required."

        self.storage = storage
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: Any, dialect: Dialect) -> Optional[str]:
        if value is None:
            return value
        if len(value.file.read(1)) != 1:
            value.file.seek(0)
            return None

        try:
            with Image.open(value.file) as image_file:
                image_file.verify()
                height, width = image_file.height, image_file.width
        except UnidentifiedImageError:
            raise ValidationException("Invalid image file")

        image = StorageImage(
            name=value.filename,
            storage=self.storage,
            height=height,
            width=width,
        )
        image.write(file=value.file)

        value.file.close()
        return image.name

    def process_result_value(
        self, value: Any, dialect: Dialect
    ) -> Optional[StorageImage]:
        if value is None:
            return value

        with Image.open(self.storage.get_path(value)) as image:
            return StorageImage(
                name=value, storage=self.storage, height=image.height, width=image.width
            )
