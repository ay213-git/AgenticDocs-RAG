import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

import ssl_dev

ssl_dev.apply_if_enabled()

from pinecone import Pinecone
from llama_index.core import Settings, VectorStoreIndex, get_response_synthesizer
from llama_index.core.llms import ChatMessage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.llms.cohere import Cohere
from llama_index.vector_stores.pinecone import PineconeVectorStore

from ui import CSS, THEME, build_demo

# ---------- הגדרות ----------
PINECONE_INDEX_NAME = "first"
PINECONE_NAMESPACE = "agentic-docs-multi"
EXTRACTED_FILE = "extracted.json"
TOP_K = 5
WIDE_TOP_K = 12
MIN_QUERY_LEN = 3
MIN_SCORE = 0.30
MAX_RETRIES = 1
MAX_STRUCTURED_ITEMS = 25

KINDS = ["decisions", "rules", "warnings", "schema_changes"]

# ---------- מודלים ----------
embed_model = CohereEmbedding(
    api_key=os.environ["COHERE_API_KEY"],
    model_name="embed-multilingual-v3.0",
    input_type="search_query",
)
llm = Cohere(
    api_key=os.environ["COHERE_API_KEY"],
    model="command-r-plus-08-2024",
    temperature=0,
)
Settings.embed_model = embed_model
Settings.llm = llm

# ---------- חיבור ל-Pinecone (חיפוש סמנטי) ----------
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
vector_store = PineconeVectorStore(
    pinecone_index=pc.Index(PINECONE_INDEX_NAME),
    namespace=PINECONE_NAMESPACE,
)
index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store, embed_model=embed_model
)
retriever_normal = VectorIndexRetriever(index=index, similarity_top_k=TOP_K)
retriever_wide = VectorIndexRetriever(index=index, similarity_top_k=WIDE_TOP_K)
synthesizer = get_response_synthesizer(llm=llm, response_mode="compact")

# ---------- טעינת הנתונים המובנים ----------
if Path(EXTRACTED_FILE).exists():
    EXTRACTED = json.loads(Path(EXTRACTED_FILE).read_text(encoding="utf-8"))
    print(f"נטען {EXTRACTED_FILE}: " + str({k: len(v) for k, v in EXTRACTED["items"].items()}))
else:
    EXTRACTED = None
    print(f"אזהרה: {EXTRACTED_FILE} לא נמצא. הניתוב יעבוד רק לחיפוש סמנטי.")


# ---------- עזרים ל-LLM ----------
async def ask_llm(prompt: str) -> str:
    """קריאה ל-Cohere דרך ה-Chat API ומחזירה טקסט."""
    response = await llm.achat([ChatMessage(role="user", content=prompt)])
    return str(response.message.content).strip()


def parse_json(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("לא נמצא JSON בתשובה")
    return json.loads(raw[start : end + 1])


def clean(value, allowed: list) -> Optional[str]:
    v = str(value).strip().lower() if value not in (None, "") else None
    return v if v in allowed else None


# ---------- Router ----------
ROUTER_PROMPT = """You are a router for a question-answering system over project documentation.
Choose exactly one route for the user's question.

semantic: explanations, descriptions, "how" or "why" questions, general questions about the project
(technologies, structure, purpose, reasons behind a choice).

structured: a database of extracted items (decisions, rules, warnings, database schema changes).
Choose it when the user asks to LIST ALL items of a kind, asks for the latest/current/active
version of a rule, limits the question by time (last week, last month), or asks which fields or
columns were added or removed.

Answer with ONE word only: semantic or structured.

Question: {question}
Answer:"""


async def choose_route(question: str) -> str:
    raw = (await ask_llm(ROUTER_PROMPT.format(question=question))).lower()
    return "structured" if "structured" in raw else "semantic"


# ---------- שאילתה מובנית ----------
QUERY_PROMPT = """Convert the user's question into a filter over a database of extracted items.
Today's date is {today}.
Kinds: decisions, rules, warnings, schema_changes.
Rules have a status: active (currently valid) or superseded (replaced by a newer rule).

Return ONLY a JSON object with these keys (use null when the question does not ask for it):
{{
  "kind": "decisions | rules | warnings | schema_changes",
  "status": "active | superseded | null   (rules only)",
  "severity": "low | medium | high | null   (warnings only)",
  "tool": "kiro | gemini | null",
  "since_days": number or null   (week = 7, month = 30),
  "keyword": "one English keyword or null"
}}

Question: {question}
JSON:"""


def build_plan(raw: dict) -> dict:
    kind = clean(raw.get("kind"), KINDS) or "decisions"
    since = raw.get("since_days")
    try:
        since = int(since) if since not in (None, "", "null") else None
    except (TypeError, ValueError):
        since = None
    keyword = raw.get("keyword")
    keyword = str(keyword).strip() if keyword not in (None, "", "null") else None
    return {
        "kind": kind,
        "status": clean(raw.get("status"), ["active", "superseded"]),
        "severity": clean(raw.get("severity"), ["low", "medium", "high"]),
        "tool": clean(raw.get("tool"), ["kiro", "gemini"]),
        "since_days": since,
        "keyword": keyword,
    }


def _item_date(item: dict):
    """תאריך הפריט כ-date; פריט בלי תאריך תקין נחשב ישן מאוד."""
    try:
        return datetime.fromisoformat(item["observed_at"][:10]).date()
    except (KeyError, TypeError, ValueError):
        return datetime.min.date()


def run_structured_query(plan: dict, use_keyword: bool = True) -> list:
    items = list(EXTRACTED["items"].get(plan["kind"], []))

    if plan["kind"] == "rules" and plan["status"]:
        items = [i for i in items if i.get("status") == plan["status"]]
    if plan["kind"] == "warnings" and plan["severity"]:
        items = [i for i in items if i.get("severity") == plan["severity"]]
    if plan["tool"]:
        items = [i for i in items if i["source"]["tool"] == plan["tool"]]
    if plan["since_days"]:
        cutoff = datetime.now().date() - timedelta(days=plan["since_days"])
        items = [i for i in items if _item_date(i) >= cutoff]
    if use_keyword and plan["keyword"]:
        kw = plan["keyword"].lower()
        items = [i for i in items if kw in json.dumps(i, ensure_ascii=False).lower()]

    items.sort(key=_item_date, reverse=True)
    return items[:MAX_STRUCTURED_ITEMS]


def compact_item(item: dict) -> dict:
    drop = {"path", "date_from_text"}
    out = {k: v for k, v in item.items() if k not in drop}
    out["source"] = {k: v for k, v in item["source"].items() if k not in drop}
    return out


ANSWER_PROMPT = """Answer the user's question using ONLY the structured items below.
List every relevant item and do not invent anything.
Answer in the same language as the question.
Mention the date and the source file of each item.
If the items include both "superseded" and "active" rules, say which one is currently valid.

Question: {question}

Items (JSON):
{items}
"""


# ---------- Events ----------
class RouteEvent(Event):
    query: str


class SearchEvent(Event):
    """בקשה לחיפוש סמנטי. wide=True אומר חיפוש רחב (ניסיון חוזר)."""
    query: str
    wide: bool = False


class StructuredQueryEvent(Event):
    query: str


class NodesRetrievedEvent(Event):
    query: str
    nodes: list


class GoodResultsEvent(Event):
    nodes: list


class StructuredResultEvent(Event):
    items: list
    plan: dict


# ---------- Workflow ----------
class RagWorkflow(Workflow):

    @step
    async def validate_input(
        self, ctx: Context, ev: StartEvent
    ) -> RouteEvent | StopEvent:
        query = (ev.get("query") or "").strip()

        if not query:
            return StopEvent(result="נא לכתוב שאלה.")
        if len(query) < MIN_QUERY_LEN:
            return StopEvent(result="השאלה קצרה מדי, נסי לפרט.")

        await ctx.store.set("original_query", query)
        await ctx.store.set("retries", 0)
        await ctx.store.set("route", "semantic")
        return RouteEvent(query=query)

    @step
    async def route(
        self, ctx: Context, ev: RouteEvent
    ) -> SearchEvent | StructuredQueryEvent:
        if EXTRACTED is None:
            return SearchEvent(query=ev.query)

        try:
            chosen = await choose_route(ev.query)
        except Exception as e:
            print(f"[router] נכשל ({e}), עוברת לחיפוש סמנטי")
            chosen = "semantic"

        print(f"[router] '{ev.query}' -> {chosen}")
        await ctx.store.set("route", chosen)

        if chosen == "structured":
            return StructuredQueryEvent(query=ev.query)
        return SearchEvent(query=ev.query)

    # ----- מסלול מובנה -----
    @step
    async def structured_lookup(
        self, ctx: Context, ev: StructuredQueryEvent
    ) -> StructuredResultEvent | SearchEvent:
        try:
            raw = await ask_llm(
                QUERY_PROMPT.format(
                    today=datetime.now().date().isoformat(), question=ev.query
                )
            )
            plan = build_plan(parse_json(raw))
            items = run_structured_query(plan)
            if not items and plan["keyword"]:
                # ולידציה: מילת המפתח אולי מגבילה מדי, מנסים בלעדיה
                items = run_structured_query(plan, use_keyword=False)
        except Exception as e:
            print(f"[structured] נכשל ({e}), חוזרת לחיפוש סמנטי")
            await ctx.store.set("route", "semantic (fallback)")
            return SearchEvent(query=ev.query)

        print(f"[structured] plan={plan} -> {len(items)} פריטים")

        if not items:
            await ctx.store.set("route", "semantic (fallback)")
            return SearchEvent(query=ev.query)

        return StructuredResultEvent(items=items, plan=plan)

    @step
    async def synthesize_structured(
        self, ctx: Context, ev: StructuredResultEvent
    ) -> StopEvent:
        original = await ctx.store.get("original_query")
        payload = json.dumps(
            [compact_item(i) for i in ev.items], ensure_ascii=False, indent=1
        )
        response = await ask_llm(
            ANSWER_PROMPT.format(question=original, items=payload)
        )

        seen, lines = set(), []
        for i in ev.items:
            key = (i["source"]["tool"], i["source"]["file"])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- **{key[0]}** / `{key[1]}`")

        return StopEvent(
            result=(
                f"{response}\n\n**מקורות:**\n" + "\n".join(lines)
                + f"\n\n*מסלול: שליפה מובנית ({ev.plan['kind']}, {len(ev.items)} פריטים)*"
            )
        )

    # ----- מסלול סמנטי -----
    @step
    async def retrieve(self, ctx: Context, ev: SearchEvent) -> NodesRetrievedEvent:
        retriever = retriever_wide if ev.wide else retriever_normal
        nodes = await retriever.aretrieve(ev.query)
        return NodesRetrievedEvent(query=ev.query, nodes=nodes)

    @step
    async def check_results(
        self, ctx: Context, ev: NodesRetrievedEvent
    ) -> GoodResultsEvent | SearchEvent | StopEvent:
        if not ev.nodes:
            return StopEvent(result="לא נמצא מידע רלוונטי במסמכים.")

        best = max((n.score or 0.0) for n in ev.nodes)
        retries = await ctx.store.get("retries", default=0)

        if best < MIN_SCORE:
            if retries < MAX_RETRIES:
                await ctx.store.set("retries", retries + 1)
                return SearchEvent(query=ev.query, wide=True)
            return StopEvent(
                result="לא נמצא מידע בביטחון מספיק. נסי לנסח את השאלה אחרת."
            )

        good = [n for n in ev.nodes if (n.score or 0.0) >= MIN_SCORE]
        return GoodResultsEvent(nodes=good)

    @step
    async def synthesize(self, ctx: Context, ev: GoodResultsEvent) -> StopEvent:
        original = await ctx.store.get("original_query")
        route_label = await ctx.store.get("route", default="semantic")
        response = await synthesizer.asynthesize(original, nodes=ev.nodes)

        seen, lines = set(), []
        for n in ev.nodes:
            meta = n.node.metadata
            key = (meta.get("tool"), meta.get("file_name"))
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"- **{meta.get('tool', '?')}** / `{meta.get('file_name', '?')}` "
                f"(ציון: {(n.score or 0.0):.2f})"
            )

        return StopEvent(
            result=(
                f"{response}\n\n**מקורות:**\n" + "\n".join(lines)
                + f"\n\n*מסלול: חיפוש {route_label}*"
            )
        )


workflow = RagWorkflow(timeout=120)


async def answer(message, history):
    try:
        result = await workflow.run(query=message)
        return str(result)
    except Exception as e:
        return f"אירעה שגיאה: {e}"


demo = build_demo(
    fn=answer,
    title="🧠 תשאול תיעוד של כלי Agentic Coding",
    subtitle="המערכת בוחרת לבד בין חיפוש סמנטי לשליפה מובנית, ומצרפת מקורות לכל תשובה.",
    badges=["🔎 חיפוש סמנטי", "🗂️ שליפה מובנית", "🧭 Router", "LlamaIndex Workflow"],
    examples=[
        "באילו טכנולוגיות משתמש פרויקט ה-todo?",
        "תן לי רשימה של כל ההחלטות הטכניות שהתקבלו בפרויקט",
        "מה הכלל העדכני לגבי אורך פונקציה?",
        "אילו דברים סומנו כרגישים בשבוע האחרון?",
        "אילו שדות נוספו או הוסרו מטבלאות קיימות?",
    ],
)

if __name__ == "__main__":
    demo.launch(theme=THEME, css=CSS)