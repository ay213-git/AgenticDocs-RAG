import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

import ssl_dev

ssl_dev.apply_if_enabled()

from llama_index.llms.cohere import Cohere
from llama_index.core.llms import ChatMessage

# ---------- הגדרות ----------
TOOLS = {
    "kiro": "Kiro-steering",
    "gemini": "Gemini-md",
}
OUTPUT_FILE = "extracted.json"
SCHEMA_VERSION = "1.0"

KINDS = ["decisions", "rules", "warnings", "schema_changes"]
PREFIXES = {"decisions": "dec", "rules": "rule", "warnings": "warn", "schema_changes": "schema"}

# ---------- הסכמה (מתוארת ל-LLM עם דוגמה) ----------
PROMPT = """You extract structured information from a documentation file written by an agentic coding tool.
File name: {file_name}

Return ONLY a JSON object (no markdown fences, no explanation) with exactly these four keys.
Each key holds a list. If the file has no items of a kind, use an empty list [] (never null).

{{
  "decisions": [
    {{"title": "short title", "summary": "what was decided and why", "tags": ["db"], "date": "YYYY-MM-DD or null", "section": "heading in the file"}}
  ],
  "rules": [
    {{"rule": "the rule text", "scope": "code | ui | testing | db | general", "notes": "or null", "status": "active | superseded", "date": "YYYY-MM-DD or null", "section": "heading"}}
  ],
  "warnings": [
    {{"area": "sensitive component", "message": "the warning text", "severity": "low | medium | high", "date": "YYYY-MM-DD or null", "section": "heading"}}
  ],
  "schema_changes": [
    {{"table": "table name", "field": "column name", "change_type": "added | removed | modified", "description": "short text", "date": "YYYY-MM-DD or null", "section": "heading"}}
  ]
}}

Guidelines:
- Extract ONLY items explicitly stated in the text. Never invent items.
- decisions: technical decisions that were made.
- rules: coding rules or guidelines. If the text says a rule was changed or replaced, add the OLD version with status "superseded" and the NEW version with status "active".
- warnings: sensitive areas or things that must not be changed carelessly. If the text says "Last reviewed: DATE", use that date.
- schema_changes: database tables or columns that were added, removed or modified.
- Use dates exactly as written in the text, in the format YYYY-MM-DD, or null.
- Write all text values in English.

---- FILE CONTENT ----
{text}
---- END ----
"""


# ---------- עזרים ----------
def file_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def valid_date(value) -> Optional[str]:
    """מחזיר YYYY-MM-DD תקין, או None."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def parse_json(raw: str) -> dict:
    """מוציא אובייקט JSON מתשובת ה-LLM, גם אם הוא עטוף בטקסט או בגדרות."""
    raw = raw.strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("לא נמצא JSON בתשובה")
    return json.loads(raw[start : end + 1])


def pick(d: dict, *names, default=None):
    """מחזיר את הערך הראשון שקיים ואינו ריק מבין שמות אפשריים."""
    for n in names:
        v = d.get(n)
        if v not in (None, "", []):
            return v
    return default


def as_str(value) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip() or None


def choice(value, allowed: list, default: str, aliases: dict = None) -> str:
    v = (as_str(value) or "").lower()
    if aliases and v in aliases:
        v = aliases[v]
    return v if v in allowed else default


# ---------- נרמול לכל סוג פריט ----------
def norm_decision(d: dict):
    summary = as_str(pick(d, "summary", "description", "text", "decision", "details"))
    title = as_str(pick(d, "title", "name", "decision"))
    if not summary and not title:
        return None
    tags = d.get("tags") if isinstance(d.get("tags"), list) else []
    return {
        "title": title or summary[:60],
        "summary": summary or title,
        "tags": [str(t) for t in tags],
    }


def norm_rule(d: dict):
    rule = as_str(pick(d, "rule", "text", "description", "name", "message"))
    if not rule:
        return None
    return {
        "rule": rule,
        "scope": as_str(pick(d, "scope", "area", "category")) or "general",
        "notes": as_str(d.get("notes")),
        "status": choice(d.get("status"), ["active", "superseded"], "active",
                         {"old": "superseded", "replaced": "superseded", "current": "active"}),
    }


def norm_warning(d: dict):
    message = as_str(pick(d, "message", "text", "description", "warning"))
    area = as_str(pick(d, "area", "name", "component", "title"))
    if not message and not area:
        return None
    return {
        "area": area or "general",
        "message": message or area,
        "severity": choice(d.get("severity"), ["low", "medium", "high"], "medium"),
    }


def norm_schema_change(d: dict):
    table = as_str(pick(d, "table", "table_name"))
    field = as_str(pick(d, "field", "column", "column_name", "name"))
    if not table and not field:
        return None
    return {
        "table": table or "unknown",
        "field": field or "unknown",
        "change_type": choice(
            pick(d, "change_type", "type", "change"),
            ["added", "removed", "modified"], "modified",
            {"add": "added", "new": "added", "remove": "removed",
             "delete": "removed", "deleted": "removed", "change": "modified", "update": "modified"},
        ),
        "description": as_str(pick(d, "description", "summary", "text")) or "",
    }


NORMALIZERS = {
    "decisions": norm_decision,
    "rules": norm_rule,
    "warnings": norm_warning,
    "schema_changes": norm_schema_change,
}


def extract_file(llm, file_name: str, text: str, attempts: int = 3) -> Optional[dict]:
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            prompt = PROMPT.format(file_name=file_name, text=text)
            response = llm.chat([ChatMessage(role="user", content=prompt)])
            return parse_json(response.message.content)
        except Exception as e:
            last_error = e
            print(f"   ניסיון {attempt} נכשל ({type(e).__name__}): ...{str(e)[-250:]}")
            time.sleep(5 * attempt)
    print("   נכשל סופית")
    return None


def main():
    print("extract.py (גרסת JSON)")
    llm = Cohere(
        api_key=os.environ["COHERE_API_KEY"],
        model="command-r-plus-08-2024",
        temperature=0,
    )

    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sources": [],
        "items": {k: [] for k in KINDS},
    }
    counters = {k: 0 for k in KINDS}

    for tool, folder in TOOLS.items():
        root = Path(folder)
        if not root.exists():
            print(f"התיקייה {folder} לא קיימת, מדלגת על {tool}")
            continue

        source = {"tool": tool, "root_path": root.as_posix(), "files": []}

        for path in sorted(root.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            modified = iso_mtime(path)
            source["files"].append(
                {"path": path.as_posix(), "last_modified": modified, "hash": file_hash(text)}
            )

            print(f"מחלצת מ-{tool}/{path.name} ...")
            data = extract_file(llm, path.name, text)
            time.sleep(3)
            if data is None:
                continue

            found = {k: 0 for k in KINDS}
            for kind in KINDS:
                raw_items = data.get(kind) or []
                if not isinstance(raw_items, list):
                    continue
                for raw_item in raw_items:
                    if not isinstance(raw_item, dict):
                        continue
                    item = NORMALIZERS[kind](raw_item)
                    if item is None:
                        continue

                    date = valid_date(raw_item.get("date"))
                    counters[kind] += 1
                    found[kind] += 1
                    entry = {"id": f"{PREFIXES[kind]}-{counters[kind]:03d}", **item}
                    entry["source"] = {
                        "tool": tool,
                        "file": path.name,
                        "path": path.as_posix(),
                        "anchor": as_str(raw_item.get("section")),
                    }
                    # תאריך מהטקסט עדיף, ואם אין, תאריך עדכון הקובץ
                    entry["observed_at"] = date or modified
                    entry["date_from_text"] = date is not None
                    result["items"][kind].append(entry)

            print("   נמצאו: " + ", ".join(f"{k}={v}" for k, v in found.items()))

        result["sources"].append(source)

    Path(OUTPUT_FILE).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nנשמר ל-{OUTPUT_FILE}")
    print({k: len(v) for k, v in result["items"].items()})


if __name__ == "__main__":
    main()