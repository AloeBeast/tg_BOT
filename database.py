import sqlite3

from config import HISTORY_LIMIT

DB_NAME = "bot_database.db"


def init_db():
    """Создаёт таблицы, если их ещё нет."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT DEFAULT '',
            facts TEXT DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()


def save_message(user_id: int, role: str, content: str):
    """Сохраняет одно сообщение в базу."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()
    conn.close()


def get_history(user_id: int, limit: int = HISTORY_LIMIT) -> list[dict[str, str]]:
    """Достаёт последние N сообщений пользователя в хронологическом порядке."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    rows.reverse()
    return [{"role": role, "content": content} for role, content in rows]


def get_user_profile(user_id: int) -> dict[str, str]:
    """Достаёт профиль пользователя (имя + факты). Если его ещё нет — создаёт пустой."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, facts FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute("INSERT INTO users (user_id, name, facts) VALUES (?, '', '')", (user_id,))
        conn.commit()
        name, facts = "", ""
    else:
        name, facts = row

    conn.close()
    return {"name": name, "facts": facts}


def update_user_name(user_id: int, name: str):
    """Обновляет имя пользователя, создавая профиль при необходимости."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (user_id, name, facts)
        VALUES (?, ?, '')
        ON CONFLICT(user_id) DO UPDATE SET name = excluded.name
        """,
        (user_id, name),
    )
    conn.commit()
    conn.close()


def append_user_fact(user_id: int, new_fact: str, max_facts: int = 8):
    """Дописывает новый факт, храня не больше max_facts последних фактов."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT facts FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute("INSERT INTO users (user_id, name, facts) VALUES (?, '', '')", (user_id,))
        current_facts = ""
    else:
        current_facts = row[0] or ""

    facts_list = [f.strip("- ").strip() for f in current_facts.split("\n") if f.strip()]
    facts_list.append(new_fact)
    facts_list = facts_list[-max_facts:]  # оставляем только последние N

    updated_facts = "\n".join(f"- {f}" for f in facts_list)

    cursor.execute("UPDATE users SET facts = ? WHERE user_id = ?", (updated_facts, user_id))
    conn.commit()
    conn.close()
