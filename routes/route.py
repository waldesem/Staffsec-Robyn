import asyncio
from datetime import UTC, datetime

from robyn import Request, Response, SubRouter

from depends.depend import (
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

    async with get_db() as conn:
        cur = await conn.cursor()
        result = await cur.execute(stmt, (*params, 11, int(page) * 10))
        candidates = [dict(cand) for cand in await result.fetchall()]
        has_next = len(candidates) > 10
        return {
            "has_next": has_next,
            "candidates": candidates[:-1] if has_next else candidates,
        }


@route.get("/persons/:person_id")
async def get_person(path_params: dict[str, str]):
    async with get_db() as conn:
        cur = await conn.cursor()
        result = await cur.execute(
            "SELECT * FROM persons WHERE id = ?", (path_params.get("person_id"),),
        )
        return dict(await result.fetchone())


@route.post("/persons")
async def post_person(request: Request):
    async with get_db() as conn:
        cur = await conn.cursor()
        user_id = get_user_id(cur)
        resume = request.json()
        resume["user_id"] = user_id

        if not (cand_id := resume.pop("id", None)):
            result = await cur.execute(
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
            )
            person = await result.fetchone()

            if not person:
                insert = await cur.execute(
                    "INSERT INTO persons ({}) VALUES ({})".format(  # noqa: S608
                        ",".join(resume.keys()),
                        ",".join(["?"] * len(resume)),
                    ),
                    tuple(resume.values()),
                )
                cand_id = insert.lastrowid

                destination = create_dest(resume | {"id": cand_id})
                await cur.execute(
                    "UPDATE persons SET destination = ? WHERE id = ?",
                    (destination, cand_id),
                )
                await conn.commit()
                return {"person_id": cand_id, "exists": False}

        await cur.execute(
            "UPDATE persons SET {} WHERE id = ?".format(  # noqa: S608
                ",".join(f"{k}=?" for k in resume),
            ),
            (*resume.values(), cand_id),
        )
        await conn.commit()
        return {"person_id": cand_id, "exists": True}


@route.delete("/persons/:person_id")
async def delete_person(path_params: dict[str, str]):
    person_id = path_params.get("person_id")
    async with get_db() as conn:
        cur = await conn.cursor()
        await asyncio.gather(
            *[
                cur.execute(
                    f"DELETE FROM {table.value} WHERE person_id = ?",  # noqa: S608
                    (person_id,),
                )
                for table in Item
            ],
        )
        await cur.execute("DELETE FROM persons WHERE id = ?", (person_id,))
        await conn.commit()
        return Response(
            status_code=204,
            headers={"Content-Type": "text/plain"},
            description="Delete item by iD",
        )


@route.get("/:item/:person_id")
async def get_item(path_params: dict[str, str]):
    async with get_db() as conn:
        cur = await conn.cursor()
        result = await cur.execute(
            f"SELECT * FROM {path_params.get('item')} WHERE person_id = ?",  # noqa: S608
            (path_params.get("person_id"),),
        )
        return [dict(res) for res in await result.fetchall()]


@route.post("/:item/:person_id")
async def post_item(request: Request):
    item = request.path_params.get("item")
    person_id = request.path_params.get("person_id")
    json_dict: dict = request.json()
    json_dict.update({"person_id": person_id, "created": datetime.now(UTC).isoformat()})

    async with get_db() as conn:
        cur = await conn.cursor()
        if item_id := json_dict.pop("id", None):
            stmt = "UPDATE {} SET {} WHERE id = ?".format(  # noqa: S608
                item,
                ",".join(f"{k}=?" for k in json_dict),
            )
            await cur.execute(stmt, (*json_dict.values(), item_id))
        else:
            stmt = "INSERT INTO {} ({}) VALUES ({})".format(  # noqa: S608
                item,
                ",".join(json_dict.keys()),
                ",".join(["?"] * len(json_dict)),
            )
            await cur.execute(stmt, tuple(json_dict.values()))
        await conn.commit()
        return Response(
            status_code=201,
            headers={"Content-Type": "text/plain"},
            description="Add or edit item by person ID",
        )


@route.delete("/:item/:item_id")
async def delete_item(path_params: dict[str, str]):
    async with get_db() as conn:
        cur = await conn.cursor()
        await cur.execute(
            f"DELETE FROM {path_params.get('item')} WHERE id = ?",  # noqa: S608
            (path_params.get("item_id"),),
        )
        await conn.commit()
        return Response(
            status_code=204,
            headers={"Content-Type": "text/plain"},
            description="Delete item by iD",
        )
