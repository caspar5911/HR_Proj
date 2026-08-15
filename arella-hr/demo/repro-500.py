"""Reproduce the employee-list 500 inside the backend container.

Copies the API endpoint's exact logic (crud.list_employees + _build_out)
and prints where it blows up.
"""

import asyncio
import traceback

from app.database import async_session
from app.crud import employee as ec
from app.api.v1.employees import _build_out  # the ACTUAL running code


def build_out(emp):
    """Use the container's real _build_out."""
    out = _build_out(emp)
    return {"id": out.id, "name": f"{out.first_name} {out.last_name}", "manager": out.manager_name}


async def main() -> None:
    async with async_session() as db:
        for page_size in (10, 20):
            print(f"--- page_size={page_size}")
            try:
                items, total = await ec.list_employees(db, page=1, page_size=page_size)
                print(f"    rows={len(items)} total={total}")
                for e in items:
                    row = build_out(e)
                    print(f"    #{row['id']} {row['name']} manager={row['manager']}")
            except Exception:
                print(f"    EXCEPTION for page_size={page_size}:")
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
