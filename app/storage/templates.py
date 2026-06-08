from typing import Any

from app.storage.sqlite import get_db


async def list_templates() -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT code, version, status, schema_version, created_at "
        "FROM agent_templates ORDER BY code, version DESC"
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_latest_template(code: str) -> dict[str, Any] | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM agent_templates WHERE code = ? AND status = 'active' "
        "ORDER BY version DESC LIMIT 1",
        (code,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def upsert_template(
    *,
    template_id: str,
    code: str,
    version: int,
    schema_version: str,
    yaml_source: str,
) -> None:
    db = await get_db()
    await db.execute(
        """
        INSERT INTO agent_templates (id, code, version, schema_version, yaml_source, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        ON CONFLICT(code, version) DO UPDATE SET
            yaml_source = excluded.yaml_source,
            schema_version = excluded.schema_version
        """,
        (template_id, code, version, schema_version, yaml_source),
    )
    await db.commit()
