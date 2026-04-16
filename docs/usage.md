## Working with storages

Often in projects, you want to get input file in the API and store it somewhere.
The `fastapi-storages` simplifies the process to store and retrieve the files
in a re-usable manner.

There are two  storages available:

- `FileSystemStorage`: To store files on the local file system.
- `S3Storage`: To store file objects in Amazon `S3` or any s3-compatible object storage.

### FileSystemStorage

A very minimal example to use `FileSystemStorage`:

```python
from fastapi import FastAPI, UploadFile
from fastapi_storages import FileSystemStorage


app = FastAPI()
storage = FileSystemStorage(path="/tmp")


@app.post("/upload/")
def create_upload_file(file: UploadFile):
    storage.write(file)
```

This will configure a `FileSystemStorage` to store files in the `/tmp` directory
and the request file is automatically saved into the destination.

### S3Storage

Now let's see a minimal example of using `S3Storage` in action:

```python
from fastapi import FastAPI, UploadFile
from fastapi_storages import S3Storage


class PublicAssetS3Storage(S3Storage):
    AWS_ACCESS_KEY_ID = "access"
    AWS_SECRET_ACCESS_KEY = "secret"
    AWS_S3_BUCKET_NAME = "test"
    AWS_S3_ENDPOINT_URL = "s3.amazonaws.com"
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_USE_SSL = True


app = FastAPI()
storage = PublicAssetS3Storage()


@app.post("/upload/")
def create_upload_file(file: UploadFile):
    storage.write(file)
```

As you can see the code is not changed and `storage.write(file)` is called the same way
it was used in `FileSystemStorage`.

!!! warning
    You should never hard-code credentials like `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in the code.
    Instead, you can read values from environment variables or as a handy way, `fastapi-storages` will use the environment variables automatically, if they are defined.

## Working with ORM extensions

The example you saw was useful, but `fastapi-storages` has ORM integrations
which makes storing and serving the files easier.

Support ORM include:

- `SQLAlchemy`
- `SQLAdmin`

### SQLAlchemy

You can use custom `SQLAlchemy` types from `fastapi-storages` for this.

Supported types include:

- `FileType`
- `ImageType`

Let's see an example:

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

As you can see the API `create_upload_file` has changed compared to using the storage directly.

You don't need the `storage.write(...)` call anymore.
With the custom SQLAlchemy types, before the model is saved in database,
the file is stored in the specified storage and then the record is saved.

You can just replace the storage with `S3Storage` and everything works without the change.
This will make your code cleaner and more readable.

#### Async Limitation

`FileType` and `ImageType` upload files synchronously inside SQLAlchemy's `process_bind_param`, which is a sync-only interface. This means file I/O (filesystem write or S3 network call) blocks the calling thread during ORM save.

For **sync SQLAlchemy** this is expected behaviour. For **async SQLAlchemy** (`AsyncSession`), SQLAlchemy uses a greenlet bridge that runs on the event loop thread, so the blocking still occurs.

!!! warning
    Avoid using `FileType` or `ImageType` with `AsyncSession` and a slow remote storage (e.g. S3) in latency-sensitive endpoints. For those cases, upload the file manually using `asyncio.to_thread` before the ORM save, and assign the resulting filename string directly to the model attribute.

#### Integration with Alembic

By default, custom types are not registered in Alembic's migrations.
To integrate these new types with Alembic, you can do either of these:

##### Create new "type" on top of these types

We create the following snippet in `custom_types.py`

```python
from fastapi_storages.integrations.sqlalchemy import FileType as _FileType
from fastapi_storages import FileSystemStorage

class FileType(_FileType):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(storage=FileSystemStorage(path='/tmp'), *args, **kwargs)
```

And by using the new `FileType` Alembic can do the imports properly, it's a simple trick, but is very simple.

##### Add files path to `script.py.mako`

Alembic allows you to modify `alembic/script.py.mako` and the migrations are generated with proper imports.

```
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
import sqlalchemy as sa
from alembic import op
import path_to_custom_types_py_file
${imports if imports else ""}

# THE REST OF SCRIPT
```

### SQLModel

If you're using sqlmodel, you'll need to annotate the type with StorageFile and enable the model's arbitrary_types_allowed configuration.

```python
from sqlmodel import SQLModel, Column, Field
from sqlmodel.main import SQLModelConfig
from fastapi_storages import FileSystemStorage
from fastapi_storages.base import StorageFile
from fastapi_storages.integrations.sqlalchemy import FileType


class Upload(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)   
    file: StorageFile = Field(
        sa_column=Column(
            FileType(storage=FileSystemStorage(path="/tmp")),
        ),
    )

    model_config = SQLModelConfig(
        arbitrary_types_allowed=True,
    )
```
