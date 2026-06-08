from pathlib import Path

import yaml

from app.factory.schema import AgentTemplateYAML
from app.internal.ids import new_id
from app.internal.logging import logger
from app.storage.templates import upsert_template


async def load_agents_from_dir(agents_dir: Path) -> None:
    if not agents_dir.exists():
        logger.warning("factory.agents_dir_missing", path=str(agents_dir))
        return

    for yaml_file in sorted(agents_dir.glob("*.yaml")):
        await _load_one(yaml_file)


async def _load_one(yaml_file: Path) -> None:
    text = yaml_file.read_text()
    raw = yaml.safe_load(text)
    template = AgentTemplateYAML.model_validate(raw)
    await upsert_template(
        template_id=new_id(),
        code=template.code,
        version=1,
        schema_version=template.schema_version,
        yaml_source=text,
    )
    logger.info("factory.template_loaded", code=template.code, file=str(yaml_file))
