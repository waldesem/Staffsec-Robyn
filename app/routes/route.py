import sqlite3
from datetime import datetime

from robyn import SubRouter, Request

from app.depends.depend import (
    Item,
    create_dest,
    create_query,
    get_user_id,
    make_dicts,
)
from config import DATABASE_URI

route = SubRouter(__file__, prefix="/routes")


@route.before_request()
async def _load_connection() -> None:
    db = sqlite3.connect(DATABASE_URI)
    db.row_factory = make_dicts
    route.inject(db=db)


@route.get("/candidates/:page")
async def get_candidates(request: Request, db: sqlite3.Connection):
    """Retrieve a paginated list of persons from the database."""
    page = request.path_params.get("page", 0)
    per_page = request.path_params.get("per_page", 10)
    query = request.query_params.to_dict()
    stmt, params = create_query(query)
    # Пагинация списка кандидатов
    with db as conn:
        cur: sqlite3.Cursor = conn.cursor()
        candidates = cur.execute(
            stmt, (*params, int(per_page) + 1, int(page) * int(per_page))
        ).fetchall()
        has_next = len(candidates) > int(per_page)
        return {
            "has_next": has_next,
            "candidates": candidates[:-1] if has_next else candidates,
        }


@route.get("/persons/:person_id")
async def get_person(request: Request, db: sqlite3.Connection):
    """Retrieve an item from the database based on the provided item ID."""
    person_id = request.path_params.get("person_id")
    with db as conn:
        cur: sqlite3.Cursor = conn.cursor()
        return cur.execute(
            "SELECT * FROM persons WHERE id = ?", (person_id,)
        ).fetchone()


@route.post("/persons")
async def post_person(request: Request, db: sqlite3.Connection):
    """Replace a record in persons table."""
    # Загружаем резюме, получаем id кандидата, а также был ли он ранее загружен
    with db as conn:
        cur: sqlite3.Cursor = conn.cursor()
        user_id = get_user_id(cur)
        resume: dict = request.json()
        resume["user_id"] = user_id

        if not (cand_id := resume.pop("id", None)):
            person = cur.execute(
                """
                    SELECT * FROM persons WHERE
                    surname=? AND firstname=? AND patronymic=? AND birthday=DATE(?)
                """,
                (
                    resume["surname"],
                    resume["firstname"],
                    resume.get("patronymic", ""),
                    resume["birthday"],
                ),
            ).fetchone()

            if not person:
                cand_id = cur.execute(
                    "INSERT INTO persons ({}) VALUES ({})".format(  # noqa: S608
                        ",".join(resume.keys()),
                        ",".join(["?"] * len(resume)),
                    ),
                    tuple(resume.values()),
                ).lastrowid

                destination = create_dest(resume | {"id": cand_id})
                cur.execute(
                    "UPDATE persons SET destination = ? WHERE id = ?",
                    (destination, cand_id),
                )
                conn.commit()
                return {"person_id": cand_id, "exists": False}

        cur.execute(
            "UPDATE persons SET {} WHERE id = ?".format(  # noqa: S608
                ",".join(f"{k}=?" for k in resume),
            ),
            (*resume.values(), cand_id),
        )
        conn.commit()
        return {"person_id": cand_id, "exists": True}


@route.delete("/persons/:person_id")
async def delete_person(request: Request, db: sqlite3.Connection):
    """Delete person from the database based on ID."""
    person_id = request.path_params.get("person_id")
    with db as conn:
        cur: sqlite3.Cursor = conn.cursor()
        for table in Item:
            cur.execute(
                f"DELETE FROM {table.value} WHERE person_id = ?",  # noqa: S608
                (person_id,),
            )
        cur.execute("DELETE FROM persons WHERE id = ?", (person_id,))
        conn.commit()
        return "", 204


@route.get("/<item>/<int:person_id>")
async def get_item(request: Request, db: sqlite3.Connection):
    """Get an item based on the provided item."""
    item = request.path_params.get("item")
    person_id = request.path_params.get("person_id")
    with db as conn:
        cur: sqlite3.Cursor = conn.cursor()
        return cur.execute(
            f"SELECT * FROM {item} WHERE person_id = ?",  # noqa: S608
            (person_id,),
        ).fetchall()


@route.post("/:item/:person_id")
async def post_item(request: Request, db: sqlite3.Connection):
    """Insert or replaces a record in the specified table."""
    item = request.path_params.get("item")
    person_id = request.path_params.get("person_id")
    json_dict: dict = request.json()
    json_dict.update({"person_id": person_id, "created": datetime.now().isoformat()})

    # Проверяем, есть ли ключ "id" в словаре json_dict
    with db as conn:
        cur: sqlite3.Cursor = conn.cursor()
        if item_id := json_dict.pop("id", None):
            # Если есть, создаем запрос на обновление записи с указанным id
            stmt = "UPDATE {} SET {} WHERE id = ?".format(  # noqa: S608
                item,
                ",".join(f"{k}=?" for k in json_dict),
            )
            cur.execute(stmt, (*json_dict.values(), item_id))
        else:
            # Если нет, создаем запрос на вставку новой записи
            stmt = "INSERT INTO {} ({}) VALUES ({})".format(  # noqa: S608
                item,
                ",".join(json_dict.keys()),
                ",".join(["?"] * len(json_dict)),
            )
            cur.execute(stmt, tuple(json_dict.values()))
        conn.commit()
        return "", 201


@route.delete("/:item>/:item_id")
async def delete_item(request: Request, db: sqlite3.Connection):
    """Delete an item from the database with provided item name and item ID."""
    item = request.path_params.get("item")
    item_id = request.path_params.get("item_id")
    with db as conn:
        cur: sqlite3.Cursor = conn.cursor()
        cur.execute(
            f"DELETE FROM {item} WHERE id = ?",  # noqa: S608
            (item_id,),
        )
        conn.commit()
        return "", 204
