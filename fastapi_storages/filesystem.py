from pathlib import Path
from typing import BinaryIO

from fastapi_storages.base import BaseStorage
from fastapi_storages.utils import secure_filename


class FileSystemStorage(BaseStorage):
    """
    File system storage which stores files in the local filesystem.
    You might want to use this with the `FileType` type.
    """

    default_chunk_size = 64 * 1024

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.mkdir(parents=True, exist_ok=True)

    def get_name(self, name: str) -> str:
        """
        Get the normalized name of the file.
        """

        parts = [s for p in Path(name).parts if (s := secure_filename(p))]
        return str(Path(*parts)) if parts else secure_filename(name)

    def get_path(self, name: str) -> str:
        """
        Get full path to the file.
        """

        return str(self._path / Path(name))

    def get_size(self, name: str) -> int:
        """
        Get file size in bytes.
        """

        return (self._path / name).stat().st_size

    def open(self, name: str) -> BinaryIO:
        """
        Open a file handle of the file object in binary mode.
        """

        path = self.get_path(name)
        return open(path, "rb")

    def write(self, file: BinaryIO, name: str) -> str:
        """
        Write input file which is opened in binary mode to destination.
        """

        filename = self.get_name(name)
        path = self.get_path(filename)

        self._path.joinpath(filename).parent.mkdir(parents=True, exist_ok=True)
        file.seek(0, 0)
        with open(path, "wb") as output:
            while True:
                chunk = file.read(self.default_chunk_size)
                if not chunk:
                    break
                output.write(chunk)

        return str(path)

    def delete(self, name: str) -> None:
        """
        Delete the file from the filesystem.
        """

        Path(self.get_path(name)).unlink()

    def generate_new_filename(self, filename: str) -> str:
        counter = 0
        prefix = Path(filename).parent
        stem = Path(filename).stem
        extension = Path(filename).suffix
        path = self._path / filename

        while path.exists():
            counter += 1
            path = self._path / prefix / f"{stem}_{counter}{extension}"

        return str(prefix / path.name)
