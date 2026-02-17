"""Utils module."""

import getpass
import sqlite3
from enum import Enum
from functools import lru_cache
from pathlib import Path

from config import BASE_PATH

class Item(Enum):
    """Item categories."""

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
def get_user_id(cur: sqlite3.Cursor) -> int | None:
    """Retrieve the current user."""
    username = getpass.getuser()
    user = cur.execute(
        "SELECT id FROM users WHERE username = ?",
        (username.lower(),),
    ).fetchone()
    return user["id"] if user else None


def create_dest(person: dict) -> str:
    """Create destination."""
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
    destination.mkdir(parents=True, exist_ok=True)
    return str(destination)


def make_dicts(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict:
    """Convert SQL row to dictionary."""
    return {cursor.description[idx][0]: value for idx, value in enumerate(row)}


def create_query(query: dict) -> tuple:
    """Create statement with params query."""
    params = []
    stmt = "SELECT id, surname, firstname, patronymic, birthday, created FROM persons"
    if query.get("search"):
        search = query["search"].upper().split(maxsplit=3)
        stmt += " WHERE surname = ?"
        params.append(search[0])
        if len(search) > 1:
            stmt += " AND firstname = ?"
            params.append(search[1])
            if len(search) > 2:
                stmt += " AND patronymic = ?"
                params.append(search[2])
    stmt += " ORDER BY id DESC LIMIT ? OFFSET ?"
    return stmt, params
