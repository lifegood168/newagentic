import asyncio

from app.internal.logging import configure_logging, logger
from app.storage.sqlite import close_db, init_db


async def main() -> None:
    configure_logging()
    logger.info("db.init.start")
    await init_db()
    await close_db()
    logger.info("db.init.complete")


if __name__ == "__main__":
    asyncio.run(main())
