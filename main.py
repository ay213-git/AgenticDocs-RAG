# # def main():
# #     print("Hello from rag-llamaindex-starter!")


# # if __name__ == "__main__":
# #     main()
# from llama_index.core import SimpleDirectoryReader


# def load_documents():
#     documents = SimpleDirectoryReader(
#         input_dir="Kiro-steering",
#         recursive=True,
#         required_exts=[".md"],
#     ).load_data()

#     for document in documents:
#         document.metadata["tool"] = "kiro"

#     return documents


# if __name__ == "__main__":
#     documents = load_documents()

#     print(f"Loaded {len(documents)} documents")

#     for document in documents:
#         print("-" * 50)
#         print(f"File: {document.metadata.get('file_name')}")
#         print(f"Tool: {document.metadata.get('tool')}")
#         print(document.text[:300])
        
import os
from dotenv import load_dotenv

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# ---- 1. תצורת הכלים - כל כלי עם התיקייה שלו ----
TOOL_DIRS = {
    "kiro": "Kiro-steering",
    # "cursor": "Cursor-docs",   # תוסיפי כשתכיני את הכלי השני
}

# ---- 2. Loading + תיוג metadata לפי כלי ----
def load_documents():
    all_documents = []
    for tool_name, dir_path in TOOL_DIRS.items():
        docs = SimpleDirectoryReader(
            input_dir=dir_path,
            recursive=True,
            required_exts=[".md"],
        ).load_data()
        for doc in docs:
            doc.metadata["tool"] = tool_name
            doc.metadata["file_name"] = doc.metadata.get("file_name", "")
        all_documents.extend(docs)
    return all_documents


# ---- 3. Chunking (MarkdownNodeParser כבר שומר Header 1/2/3 ב-metadata אוטומטית) ----
def create_nodes(documents):
    parser = MarkdownNodeParser()
    nodes = parser.get_nodes_from_documents(documents)
    return nodes


# ---- 4. Embedding עם Cohere (embed-v4.0 - הדגם הרב-לשוני העדכני, תומך עברית) ----
def setup_embedding_model():
    embed_model = CohereEmbedding(
        api_key=os.environ["COHERE_API_KEY"],
        model_name="embed-v4.0",
        input_type="search_document",
        embedding_types=["float"],
    )
    Settings.embed_model = embed_model
    return embed_model


# ---- 5. Pinecone + בניית ה-Index ----
def setup_pinecone_index(dimension: int = 1536):
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index_name = "agentic-docs-rag"

    existing = [i.name for i in pc.list_indexes()]
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    pinecone_index = pc.Index(index_name)
    vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
    return StorageContext.from_defaults(vector_store=vector_store)


def build_index():
    documents = load_documents()
    nodes = create_nodes(documents)
    setup_embedding_model()
    storage_context = setup_pinecone_index()

    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
    )
    return index


if __name__ == "__main__":
    index = build_index()
    print("✅ Index נבנה ונשמר ב-Pinecone")