# import os

# from dotenv import load_dotenv

# load_dotenv()

# import ssl_dev

# ssl_dev.apply_if_enabled()

# import gradio as gr
# from pinecone import Pinecone
# from llama_index.core import VectorStoreIndex, Settings, get_response_synthesizer
# from llama_index.core.retrievers import VectorIndexRetriever
# from llama_index.core.postprocessor import SimilarityPostprocessor
# from llama_index.core.query_engine import RetrieverQueryEngine
# from llama_index.embeddings.cohere import CohereEmbedding
# from llama_index.llms.cohere import Cohere
# from llama_index.vector_stores.pinecone import PineconeVectorStore

# # ---------- הגדרות (חייבות להיות זהות לאלה שב-prepare.py) ----------
# PINECONE_INDEX_NAME = "first"
# PINECONE_NAMESPACE = "agentic-docs-multi"
# TOP_K = 5
# MIN_SIMILARITY = 0.2

# # ---------- מודלים ----------
# embed_model = CohereEmbedding(
#     api_key=os.environ["COHERE_API_KEY"],
#     model_name="embed-multilingual-v3.0",
#     input_type="search_query",  # בשאילתות משתמשים ב-search_query
# )

# llm = Cohere(
#     api_key=os.environ["COHERE_API_KEY"],
#     model="command-r-plus-08-2024",
# )

# Settings.embed_model = embed_model
# Settings.llm = llm

# # ---------- חיבור לאינדקס הקיים ב-Pinecone ----------
# pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
# pinecone_index = pc.Index(PINECONE_INDEX_NAME)
# vector_store = PineconeVectorStore(
#     pinecone_index=pinecone_index, namespace=PINECONE_NAMESPACE
# )
# index = VectorStoreIndex.from_vector_store(
#     vector_store=vector_store, embed_model=embed_model
# )

# # ---------- 1. Retrieve ----------
# retriever = VectorIndexRetriever(index=index, similarity_top_k=TOP_K)

# # ---------- 2. Postprocessing ----------
# postprocessor = SimilarityPostprocessor(similarity_cutoff=MIN_SIMILARITY)

# # ---------- 3. Synthesizing ----------
# response_synthesizer = get_response_synthesizer(llm=llm, response_mode="compact")

# query_engine = RetrieverQueryEngine(
#     retriever=retriever,
#     node_postprocessors=[postprocessor],
#     response_synthesizer=response_synthesizer,
# )


# def format_sources(response) -> str:
#     if not response.source_nodes:
#         return ""
#     lines = []
#     seen = set()
#     for node in response.source_nodes:
#         meta = node.node.metadata
#         key = (meta.get("tool"), meta.get("file_name"))
#         if key in seen:
#             continue
#         seen.add(key)
#         score = node.score if node.score is not None else 0.0
#         lines.append(
#             f"- **{meta.get('tool', '?')}** / `{meta.get('file_name', '?')}` "
#             f"(ציון: {score:.2f})"
#         )
#     return "\n\n**מקורות:**\n" + "\n".join(lines)


# def answer(message, history):
#     if not message or not message.strip():
#         return "נא לכתוב שאלה."
#     try:
#         response = query_engine.query(message)
#     except Exception as e:
#         return f"אירעה שגיאה: {e}"

#     if not response.source_nodes:
#         return "לא נמצא מידע רלוונטי במסמכים."

#     return str(response) + format_sources(response)


# demo = gr.ChatInterface(
#     fn=answer,
#     title="תשאול תיעוד של כלי Agentic Coding",
#     description="שאלי שאלות על קבצי ה-md של הכלים (Kiro ו-Gemini).",
#     examples=[
#         "What is the main purpose of the product?",
#         "What technologies does the project use?",
#         "How is the project structured?",
#     ],
# )

# if __name__ == "__main__":
#     demo.launch()
import os

from dotenv import load_dotenv

load_dotenv()

import ssl_dev

ssl_dev.apply_if_enabled()

from pinecone import Pinecone
from llama_index.core import VectorStoreIndex, Settings, get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.llms.cohere import Cohere
from llama_index.vector_stores.pinecone import PineconeVectorStore

from ui import CSS, THEME, build_demo

# ---------- הגדרות (חייבות להיות זהות לאלה שב-prepare.py) ----------
PINECONE_INDEX_NAME = "first"
PINECONE_NAMESPACE = "agentic-docs-multi"
TOP_K = 5
MIN_SIMILARITY = 0.2

# ---------- מודלים ----------
embed_model = CohereEmbedding(
    api_key=os.environ["COHERE_API_KEY"],
    model_name="embed-multilingual-v3.0",
    input_type="search_query",  # בשאילתות משתמשים ב-search_query
)

llm = Cohere(
    api_key=os.environ["COHERE_API_KEY"],
    model="command-r-plus-08-2024",
)

Settings.embed_model = embed_model
Settings.llm = llm

# ---------- חיבור לאינדקס הקיים ב-Pinecone ----------
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
pinecone_index = pc.Index(PINECONE_INDEX_NAME)
vector_store = PineconeVectorStore(
    pinecone_index=pinecone_index, namespace=PINECONE_NAMESPACE
)
index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store, embed_model=embed_model
)

# ---------- 1. Retrieve ----------
retriever = VectorIndexRetriever(index=index, similarity_top_k=TOP_K)

# ---------- 2. Postprocessing ----------
postprocessor = SimilarityPostprocessor(similarity_cutoff=MIN_SIMILARITY)

# ---------- 3. Synthesizing ----------
response_synthesizer = get_response_synthesizer(llm=llm, response_mode="compact")

query_engine = RetrieverQueryEngine(
    retriever=retriever,
    node_postprocessors=[postprocessor],
    response_synthesizer=response_synthesizer,
)


def format_sources(response) -> str:
    if not response.source_nodes:
        return ""
    lines = []
    seen = set()
    for node in response.source_nodes:
        meta = node.node.metadata
        key = (meta.get("tool"), meta.get("file_name"))
        if key in seen:
            continue
        seen.add(key)
        score = node.score if node.score is not None else 0.0
        lines.append(
            f"- **{meta.get('tool', '?')}** / `{meta.get('file_name', '?')}` "
            f"(ציון: {score:.2f})"
        )
    return "\n\n**מקורות:**\n" + "\n".join(lines)


def answer(message, history):
    if not message or not message.strip():
        return "נא לכתוב שאלה."
    try:
        response = query_engine.query(message)
    except Exception as e:
        return f"אירעה שגיאה: {e}"

    if not response.source_nodes:
        return "לא נמצא מידע רלוונטי במסמכים."

    return str(response) + format_sources(response)


demo = build_demo(
    fn=answer,
    title="🧠 תשאול תיעוד של כלי Agentic Coding",
    subtitle="שאלי שאלות על קבצי ה-md של הכלים (Kiro ו-Gemini) וקבלי תשובה עם מקורות.",
    badges=["🔎 חיפוש סמנטי", "Cohere", "Pinecone"],
    examples=[
        "What is the main purpose of the product?",
        "What technologies does the project use?",
        "How is the project structured?",
    ],
)

if __name__ == "__main__":
    demo.launch(theme=THEME, css=CSS)