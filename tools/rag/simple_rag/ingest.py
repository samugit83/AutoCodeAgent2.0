import os
import chromadb
from models.models import create_embeddings
from uuid import uuid4  # For generating unique IDs
from params import PARAMS

def split_text_into_chunks(text, max_chars, overlap):
    """
    Splits a large text into smaller chunks with a specified max length and optional overlap.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunk = text[start:end]
        if end < len(text):
            overlap_start = max(0, end - overlap)
            start = overlap_start
        else:
            start = end
        chunks.append(chunk.strip())
    return chunks


def ingest_texts(texts, collection_name="simple_rag"):

    """
    Ingests a list of text strings into the Chroma vector store using OpenAI embeddings.
    Utilizes a persistent Chroma client to save data across sessions.
    """
    model = PARAMS["SIMPLE_RAG_EMBEDDING_MODEL"]
    max_chunk_size = PARAMS["SIMPLE_RAG_CHUNK_SIZE"]
    overlap = PARAMS["SIMPLE_RAG_OVERLAP"]
    db_path = PARAMS["CHROMA_DB_PATH"]
    
    if not texts:
        raise ValueError("No texts provided for ingestion.")
    
    all_chunks = []
    for text in texts:
        if len(text.strip()) > max_chunk_size:
            chunks = split_text_into_chunks(text, max_chars=max_chunk_size, overlap=overlap)
            all_chunks.extend(chunks)
        else:
            all_chunks.append(text.strip())

    if not all_chunks:
        raise ValueError("No valid text found in the provided inputs.")

    docs = []
    for chunk in all_chunks:
        unique_id = str(uuid4())  
        docs.append({
            'id': unique_id,
            'text': chunk,
            'metadata': {'collection_name': collection_name}
        })

    texts_to_embed = [doc['text'] for doc in docs]

    embeddings = create_embeddings(texts_to_embed, model=model)  

    try:
        client = chromadb.PersistentClient(path=db_path)
    except TypeError as e:
        raise RuntimeError(f"Error initializing Chroma client: {e}") 

    collection = client.get_or_create_collection(name=collection_name)

    ids = [doc['id'] for doc in docs]
    metadatas = [doc['metadata'] for doc in docs] 

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts_to_embed,
        metadatas=metadatas
    )

    return {
        "status": "success",
        "message": f"Successfully ingested {len(docs)} documents into the database."
    }


