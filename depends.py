import getpass
from contextlib import asynccontextmanager
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite

from config import BASE_PATH, DATABASE_URI

if TYPE_CHECKING:
    from types import AsyncGeneratorType


class Item(Enum):
    ADDRESSES = "addresses"
    AFFILATIONS = "affilations"
    CHECKS = "checks"
    CONTACTS = "contacts"
    DOCUMENTS = "documents"
    EDUCATIONS = "educations"
    INQUIRIES = "inquiries"
    INVESTIGATIONS = "investigations"
    PREVIOUS = "previous"
    POLIGRAFS = "poligrafs"
    STAFFS = "staffs"
    WORKPLACES = "workplaces"


@lru_cache
async def get_user_id(cur: aiosqlite.Cursor) -> int | None:
    username = getpass.getuser()
    result = await cur.execute(
        "SELECT id FROM users WHERE username = ?",
        (username.lower(),),
    )
    user = await result.fetchone()
    return user["id"] if user else None


def create_dest(person: dict) -> str:
    destination = Path(
        BASE_PATH,
        "Главный офис",
        person["surname"][0],
        "{}-{} {} {}".format(
            person["id"],
            person["surname"],
            person["firstname"],
            person.get("patronymic", ""),
        ).rstrip(),
    )
    return str(destination)


@asynccontextmanager
async def get_db() -> AsyncGeneratorType[aiosqlite.Connection]:
    db = await aiosqlite.connect(DATABASE_URI)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        pass
