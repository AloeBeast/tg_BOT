import logging
import ssl as ssl_module

import asyncpg

from config import DATABASE_URL, DB_POOL_MAX, DB_POOL_MIN, HISTORY_LIMIT

logger = logging.getLogger(__name__)
_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = DATABASE_URL.split("?")[0]
        ssl_ctx = ssl_module.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl_module.CERT_NONE

        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=DB_POOL_MIN,
            max_size=DB_POOL_MAX,
            command_timeout=30,
            ssl=ssl_ctx,
        )
        logger.info("DB pool created (min=%s, max=%s)", DB_POOL_MIN, DB_POOL_MAX)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("DB pool closed")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized; call init_pool() at startup")
    return _pool


async def init_db() -> None:
    """Создаёт таблицы и индексы, если их ещё нет."""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    BIGINT PRIMARY KEY,
                name       TEXT NOT NULL DEFAULT '',
                facts      TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         BIGSERIAL PRIMARY KEY,
                user_id    BIGINT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_user_id_id "
            "ON messages (user_id, id DESC)"
        )

        await conn.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ"
        )

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS stats_daily (
                date       DATE NOT NULL,
                user_id    BIGINT NOT NULL,
                messages   INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (date, user_id)
            )
        """)


async def save_message(user_id: int, role: str, content: str) -> None:
    """Сохраняет одно сообщение в базу."""
    await get_pool().execute(
        "INSERT INTO messages (user_id, role, content) VALUES ($1, $2, $3)",
        user_id, role, content,
    )


async def track_user_activity(user_id: int) -> None:
    """Отмечает активность пользователя — обновляет last_active_at и счётчик за день.

    Эти данные не удаляются при очистке истории и служат для точной статистики.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET last_active_at = NOW() WHERE user_id = $1",
            user_id,
        )
        await conn.execute(
            """
            INSERT INTO stats_daily (date, user_id, messages)
            VALUES (CURRENT_DATE, $1, 1)
            ON CONFLICT (date, user_id) DO UPDATE
                SET messages = stats_daily.messages + 1
            """,
            user_id,
        )


async def get_history(user_id: int, limit: int = HISTORY_LIMIT) -> list[dict[str, str]]:
    """Достаёт последние N сообщений пользователя в хронологическом порядке."""
    rows = await get_pool().fetch(
        "SELECT role, content FROM messages "
        "WHERE user_id = $1 ORDER BY id DESC LIMIT $2",
        user_id, limit,
    )
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def get_user_profile(user_id: int) -> dict[str, str]:
    """Достаёт профиль пользователя (имя + факты). Если его ещё нет — создаёт пустой."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT name, facts FROM users WHERE user_id = $1", user_id,
    )
    if row is None:
        await pool.execute(
            "INSERT INTO users (user_id) VALUES ($1)", user_id,
        )
        return {"name": "", "facts": ""}
    return {"name": row["name"], "facts": row["facts"]}


async def update_user_name(user_id: int, name: str) -> None:
    """Обновляет имя пользователя, создавая профиль при необходимости."""
    await get_pool().execute(
        """
        INSERT INTO users (user_id, name)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE
            SET name = EXCLUDED.name, updated_at = NOW()
        """,
        user_id, name,
    )


async def append_user_fact(user_id: int, new_fact: str, max_facts: int = 8) -> None:
    """Дописывает новый факт, храня не больше max_facts последних фактов."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO users (user_id) VALUES ($1) "
                "ON CONFLICT (user_id) DO NOTHING",
                user_id,
            )
            row = await conn.fetchrow(
                "SELECT facts FROM users WHERE user_id = $1 FOR UPDATE", user_id,
            )
            current = row["facts"] if row else ""

            facts_list = [f.strip("- ").strip() for f in current.split("\n") if f.strip()]
            facts_list.append(new_fact)
            facts_list = facts_list[-max_facts:]

            updated_facts = "\n".join(f"- {f}" for f in facts_list)

            await conn.execute(
                "UPDATE users SET facts = $1, updated_at = NOW() WHERE user_id = $2",
                updated_facts, user_id,
            )


async def clear_user_history(user_id: int) -> None:
    """Удаляет всю историю сообщений пользователя."""
    await get_pool().execute(
        "DELETE FROM messages WHERE user_id = $1", user_id,
    )


async def reset_user_profile(user_id: int) -> None:
    """Сбрасывает имя и факты пользователя, сохраняя строку (user_id)."""
    await get_pool().execute(
        "UPDATE users SET name = '', facts = '', updated_at = NOW() "
        "WHERE user_id = $1",
        user_id,
    )


async def get_stats() -> dict[str, int]:
    """Возвращает статистику по боту (не зависит от очистки истории пользователями)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        today_users = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE last_active_at >= CURRENT_DATE"
        )
        today_messages = await conn.fetchval(
            "SELECT COALESCE(SUM(messages), 0) FROM stats_daily "
            "WHERE date = CURRENT_DATE"
        )
    return {
        "total_users": total_users,
        "today_users": today_users,
        "today_messages": today_messages,
    }
