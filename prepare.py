import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import ssl_dev

ssl_dev.apply_if_enabled()

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

# ---------- הגדרות ----------
TOOLS = {
    "kiro": "Kiro-steering",
    "gemini": "Gemini-md",
}

PINECONE_INDEX_NAME = "first"
PINECONE_NAMESPACE = "agentic-docs-multi"
EMBED_DIMENSION = 1024  # embed-multilingual-v3.0


# ---------- 1. Loading ----------
def extract_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def load_documents():
    all_docs = []
    for tool, folder in TOOLS.items():
        if not Path(folder).exists():
            print(f"התיקייה {folder} לא קיימת, מדלגת על {tool}")
            continue

        reader = SimpleDirectoryReader(
            input_dir=folder,
            required_exts=[".md"],
            recursive=True,
        )
        docs = reader.load_data()

        for doc in docs:
            file_path = doc.metadata.get("file_path", "")
            file_name = doc.metadata.get("file_name", "")
            doc.metadata = {
                "tool": tool,
                "file_name": file_name,
                "file_path": file_path,
                "title": extract_title(doc.text, file_name),
                "last_modified": doc.metadata.get("last_modified_date", ""),
            }
            doc.excluded_embed_metadata_keys = ["file_path", "last_modified"]
            doc.excluded_llm_metadata_keys = ["file_path"]

        print(f"{tool}: נטענו {len(docs)} קבצים")
        all_docs.extend(docs)
    return all_docs


# ---------- 2. Chunking ----------
def chunk_documents(documents):
    md_parser = MarkdownNodeParser()
    section_nodes = md_parser.get_nodes_from_documents(documents)

    splitter = SentenceSplitter(chunk_size=500, chunk_overlap=20)
    nodes = splitter.get_nodes_from_documents(section_nodes, show_progress=True)
    return nodes


# ---------- 3-5. Embedding + Index + Pinecone ----------
def get_or_create_pinecone_index(pc: Pinecone):
    existing = [i.name for i in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        print(f"יוצרת אינדקס {PINECONE_INDEX_NAME}...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBED_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # מחכים שהאינדקס יהיה מוכן
        for _ in range(30):
            status = pc.describe_index(PINECONE_INDEX_NAME).status
            ready = status["ready"] if isinstance(status, dict) else status.ready
            if ready:
                break
            time.sleep(2)
        print("האינדקס מוכן")
    return pc.Index(PINECONE_INDEX_NAME)


def build_index(nodes):
    embed_model = CohereEmbedding(
        api_key=os.environ["COHERE_API_KEY"],
        model_name="embed-multilingual-v3.0",
        input_type="search_document",
    )

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    pinecone_index = get_or_create_pinecone_index(pc)

    vector_store = PineconeVectorStore(
        pinecone_index=pinecone_index, namespace=PINECONE_NAMESPACE
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    return VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )


if __name__ == "__main__":
    documents = load_documents()
    print(f"סה״כ מסמכים: {len(documents)}")

    nodes = chunk_documents(documents)
    print(f"סה״כ chunks: {len(nodes)}")

    build_index(nodes)
    print("האינדוקס הסתיים ונשמר ב-Pinecone")