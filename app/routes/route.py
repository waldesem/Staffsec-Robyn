import sqlite3
from datetime import datetime

from robyn import SubRouter, Request

from app.depends.depend import (
    Item,
    create_dest,
    get_db,
    get_user_id,
)

route = SubRouter(__file__, prefix="/routes")


@route.get("/candidates/:page")
async def get_candidates(request: Request):
    page = request.path_params.get("page", 0)
    query = request.query_params.get("search", None)
    params = []
    stmt = "SELECT id, surname, firstname, patronymic, birthday, created FROM persons"
    if query:
        search = query.upper().split(maxsplit=3)
        stmt += " WHERE surname = ?"
        params.append(search[0])
        if len(search) > 1:
            stmt += " AND firstname = ?"
            params.append(search[1])
            if len(search) > 2:
                stmt += " AND patronymic = ?"
                params.append(search[2])
    stmt += " ORDER BY id DESC LIMIT ? OFFSET ?"

    with get_db() as conn:
        cur: sqlite3.Cursor = conn.cursor()
        candidates = cur.execute(stmt, (*params, 11, int(page) * 10)).fetchall()
        has_next = len(candidates) > 10
        return {
            "has_next": has_next,
            "candidates": candidates[:-1] if has_next else candidates,
        }


@route.get("/persons/:person_id")
async def get_person(request: Request):
    person_id = request.path_params.get("person_id")
    with get_db() as conn:
        cur: sqlite3.Cursor = conn.cursor()
        return cur.execute(
            "SELECT * FROM persons WHERE id = ?", (person_id,)
        ).fetchone()


@route.post("/persons")
async def post_person(request: Request):
    with get_db() as conn:
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
async def delete_person(request: Request):
    person_id = request.path_params.get("person_id")
    with get_db() as conn:
        cur: sqlite3.Cursor = conn.cursor()
        for table in Item:
            cur.execute(
                f"DELETE FROM {table.value} WHERE person_id = ?",  # noqa: S608
                (person_id,),
            )
        cur.execute("DELETE FROM persons WHERE id = ?", (person_id,))
        conn.commit()
        return "", 204


@route.get("/:item/:person_id")
async def get_item(request: Request):
    item = request.path_params.get("item")
    person_id = request.path_params.get("person_id")
    with get_db() as conn:
        cur: sqlite3.Cursor = conn.cursor()
        return cur.execute(
            f"SELECT * FROM {item} WHERE person_id = ?",  # noqa: S608
            (person_id,),
        ).fetchall()


@route.post("/:item/:person_id")
async def post_item(request: Request):
    """Insert or replaces a record in the specified table."""
    item = request.path_params.get("item")
    person_id = request.path_params.get("person_id")
    json_dict: dict = request.json()
    json_dict.update({"person_id": person_id, "created": datetime.now().isoformat()})

    with get_db() as conn:
        cur: sqlite3.Cursor = conn.cursor()
        if item_id := json_dict.pop("id", None):
            stmt = "UPDATE {} SET {} WHERE id = ?".format(  # noqa: S608
                item,
                ",".join(f"{k}=?" for k in json_dict),
            )
            cur.execute(stmt, (*json_dict.values(), item_id))
        else:
            stmt = "INSERT INTO {} ({}) VALUES ({})".format(  # noqa: S608
                item,
                ",".join(json_dict.keys()),
                ",".join(["?"] * len(json_dict)),
            )
            cur.execute(stmt, tuple(json_dict.values()))
        conn.commit()
        return "", 201


@route.delete("/:item/:item_id")
async def delete_item(request: Request):
    item = request.path_params.get("item")
    item_id = request.path_params.get("item_id")
    with get_db() as conn:
        cur: sqlite3.Cursor = conn.cursor()
        cur.execute(
            f"DELETE FROM {item} WHERE id = ?",  # noqa: S608
            (item_id,),
        )
        conn.commit()
        return "", 204
