import os
import re
from typing import Union, overload

_filename_ascii_strip_re = re.compile(r"[^A-Za-z0-9_.-]")


@overload
def lookup_env(name: str, default: bool) -> bool: ...


@overload
def lookup_env(name: str, default: str = ...) -> str: ...


def lookup_env(name: str, default: Union[str, bool] = "") -> Union[str, bool]:
    """
    Read environment variable with type coercion.
    If default is bool, coerce the env value: "true", "1", "yes" -> True, else False.
    If env var not set, return default.
    """
    value = os.environ.get(name)
    if value is None:
        return default
    if isinstance(default, bool):
        return value.lower() in ("true", "1", "yes")
    return value


def secure_filename(filename: str) -> str:
    """
    From Werkzeug secure_filename.
    """

    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")

    normalized_filename = _filename_ascii_strip_re.sub("", "_".join(filename.split()))
    filename = str(normalized_filename).strip("._")
    return filename
