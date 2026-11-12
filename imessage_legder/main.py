import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from ollama import chat
from pydantic import BaseModel, ValidationError

MODEL_NAME = "llama3.2"
BATCH_SIZE = 10
TRANSACTION_DB = "transaction.db"
IMESSAGE_DB = "~/Library/Messages/chat.db"

TransactionRow = Dict[str, object]


class TransactionCategory(str, Enum):
    food = "food"
    transport = "transport"
    groceries = "groceries"
    entertainment = "entertainment"
    utilities = "utilities"
    other = "other"


class TransactionBatchItem(BaseModel):
    amount: float
    date: datetime
    time: str
    vendor: str
    transaction_number: str
    category: TransactionCategory
    guid: str
    text: str

class TransactionBatch(BaseModel):
    transactions: List[TransactionBatchItem]

FORMAT_SCHEMA = TransactionBatch.model_json_schema()
FORMAT_SCHEMA_JSON = json.dumps(FORMAT_SCHEMA, indent=2)

SYSTEM_PROMPT = (
    "You must return ONLY valid JSON that matches the provided JSON Schema. "
    "Do not include any explanations or additional text. "
    "If you cannot extract any valid transactions, return {\"transactions\": []}. "
    "The message will contain a batch of SMS messages about financial transactions. Extract structured data for each message that contains a transaction. "
    "Only include parsed transaction objects for valid transactions. "
    "Each item must contain guid and original text so it can be mapped back to the message. "
    "- amount: The total amount of the transaction "
    "- date: The date of the transaction in YYYY-MM-DD format "
    "- time: The time of the transaction in HH:MM:SS format "
    "- vendor: The name of the vendor or merchant involved in the transaction "
    "- transaction_number: The reference or transaction ID "
    "- category: The transaction category\n\n"
    "Schema:\n"
    f"{FORMAT_SCHEMA_JSON}"
)


def resolve_imessage_db_path(path: str = IMESSAGE_DB) -> str:
    return os.path.expanduser(path)


def fetch_imessages_after(
    date_str: str,
    batch_size: int = BATCH_SIZE,
    db_path: str = IMESSAGE_DB,
) -> Iterator[List[TransactionRow]]:
    db_path = resolve_imessage_db_path(db_path)
    query = """
    SELECT guid,
           text,
           date,
           datetime(date / 1000000000.0 + 978307200, 'unixepoch') AS iso_date
    FROM message
    WHERE datetime(date / 1000000000.0 + 978307200, 'unixepoch') > ?
    ORDER BY date;
    """

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, (date_str,))

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            yield [dict(row) for row in rows]


def ensure_transaction_table(db_path: str = TRANSACTION_DB) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT UNIQUE,
                text TEXT,
                date TEXT,
                time TEXT,
                vendor TEXT,
                amount REAL,
                category TEXT,
                transaction_number TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def save_transactions(
    transactions: List[TransactionBatchItem],
    db_path: str = TRANSACTION_DB,
) -> int:
    if not transactions:
        return 0

    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO transactions (
                guid,
                text,
                date,
                time,
                vendor,
                amount,
                category,
                transaction_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    transaction.guid,
                    transaction.text,
                    transaction.date.strftime("%Y-%m-%d"),
                    transaction.time,
                    transaction.vendor,
                    transaction.amount,
                    transaction.category.value,
                    transaction.transaction_number,
                )
                for transaction in transactions
            ],
        )
        conn.commit()
        return conn.execute("SELECT changes();").fetchone()[0]


def _build_batch_prompt(batch: List[TransactionRow]) -> str:
    parts = []
    for row in batch:
        guid = row.get("guid", "")
        text = str(row.get("text", "")).replace("\n", " ").strip()
        parts.append(f"GUID: {guid}\nTEXT: {text}")
    return (
        "Parse the following messages into a JSON list of transaction objects. "
        "Only include entries for messages that contain a valid financial transaction. "
        "Preserve guid and text for each parsed transaction.\n\n"
        + "\n\n".join(parts)
    )


def parse_transaction_batch(batch: List[TransactionRow]) -> List[TransactionBatchItem]:
    if not batch:
        return []

    response = chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_batch_prompt(batch)},
        ],
        format=FORMAT_SCHEMA,
        options={"temperature": 0},
    )

    if not hasattr(response, "message") or not hasattr(response.message, "content"):
        logging.warning("Unexpected LLM response shape for transaction batch")
        return []

    try:
        batch_list = TransactionBatch.model_validate_json(response.message.content)
        return [transaction for transaction in batch_list.transactions if transaction.amount and transaction.vendor]
    except (ValidationError, json.JSONDecodeError) as exc:
        logging.warning("Batch parse failed: %s", exc)
        return []


def process_imessages_after(
    date_str: str,
    batch_size: int = BATCH_SIZE,
    imessage_db: str = IMESSAGE_DB,
    transaction_db: str = TRANSACTION_DB,
) -> int:
    ensure_transaction_table(transaction_db)
    processed = 0

    for batch in fetch_imessages_after(date_str, batch_size, imessage_db):
        parsed_transactions = parse_transaction_batch(batch)
        processed += save_transactions(parsed_transactions, transaction_db)

    return processed


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch iMessages after a given date and save parsed transactions to SQLite."
    )
    parser.add_argument(
        "since_date",
        help="ISO date string to filter iMessages, e.g. 2026-06-10",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Number of messages to fetch per SQLite batch.",
    )
    parser.add_argument(
        "--imessage-db",
        default=IMESSAGE_DB,
        help="Path to the iMessage chat.db file.",
    )
    parser.add_argument(
        "--transaction-db",
        default=TRANSACTION_DB,
        help="Path to the transaction SQLite database.",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_arg_parser()
    args = parser.parse_args()

    if not Path(resolve_imessage_db_path(args.imessage_db)).exists():
        logging.error("iMessage database not found: %s", args.imessage_db)
        return 1

    total = process_imessages_after(
        args.since_date,
        batch_size=args.batch_size,
        imessage_db=args.imessage_db,
        transaction_db=args.transaction_db,
    )

    logging.info("Processed %d transactions from iMessage after %s", total, args.since_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

