<p align="center">
<a href="https://github.com/smithyhq/fastapi-storages">
    <img width="500px" src="https://raw.githubusercontent.com/smithyhq/fastapi-storages/main/docs/assets/images/banner.png" alt"FastAPI_Storages">
</a>
</p>

<p align="center">
<a href="https://github.com/smithyhq/fastapi-storages/actions">
    <img src="https://github.com/smithyhq/fastapi-storages/workflows/Tests/badge.svg" alt="Build Status">
</a>
<a href="https://github.com/smithyhq/fastapi-storages/actions">
    <img src="https://github.com/smithyhq/fastapi-storages/workflows/Publish/badge.svg" alt="Publish Status">
</a>
<a href="https://codecov.io/gh/smithyhq/fastapi-storages">
    <img src="https://codecov.io/gh/smithyhq/fastapi-storages/branch/main/graph/badge.svg" alt="Coverage">
</a>
<a href="https://pypi.org/project/fastapi-storages/">
    <img src="https://badge.fury.io/py/fastapi-storages.svg" alt="Package version">
</a>
<a href="https://pypi.org/project/fastapi-storages" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/fastapi-storages.svg?color=%2334D058" alt="Supported Python versions">
</a>
</p>

---

# FastAPI Storages

A collection of backend storages and ORM extensions to simplify file management in FastAPI and Starlette projects.

Similar to `django-storages` project, but aiming to work with a wider range of database ORMs and backends.

---

**Documentation**: [https://smithyhq.github.io/fastapi-storages](https://smithyhq.github.io/fastapi-storages)

**Source Code**: [https://github.com/smithyhq/fastapi-storages](https://github.com/smithyhq/fastapi-storages)

---

## Installation

```console
pip install fastapi-storages
pip install 'fastapi-storages[full]'
```

## Supported integrations

- `SQLAlchemy`
- `SQLModel`
- `SQLAdmin`

## Supported storage backends

- `FileSystemStorage`
- `S3Storage`

## Example

```python
from fastapi import FastAPI, UploadFile
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import Session, declarative_base
from fastapi_storages import FileSystemStorage
from fastapi_storages.integrations.sqlalchemy import FileType

app = FastAPI()
Base = declarative_base()
engine = create_engine("sqlite:///test.db")


class Example(Base):
    __tablename__ = "example"

    id = Column(Integer, primary_key=True)
    file = Column(FileType(storage=FileSystemStorage(path="/tmp")))


# Create database and table
Base.metadata.create_all(engine)


@app.post("/upload/")
def create_upload_file(file: UploadFile):
    example = Example(file=file)
    with Session(engine) as session:
        session.add(example)
        session.commit()
        return {"filename": example.file.name}
```