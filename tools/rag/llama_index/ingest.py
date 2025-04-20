import os
from llama_index.core import VectorStoreIndex, Document, StorageContext, load_index_from_storage
from params import PARAMS

def ingest_texts(texts):
    """
    Ingest a list of raw text strings into a LlamaIndex vector store.
    This function:
      - Loads environment variables (including OPENAI_API_KEY) from your environment.
      - Instantiates an OpenAI embedding model.
      - Checks for an existing index in the specified directory and appends new documents,
        or creates a new index if none exists.
      - Persists the updated index back to disk using the storage_context.persist() method.
    
    Parameters:
      texts (List[str]): A list of text strings to ingest.
      db_dir (str): Directory where the index files will be stored.
    
    Returns:
      dict: A status message.
    """
    db_dir = PARAMS["LLAMA_INDEX_DB_PATH"]
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in environment. Check your .env file.")

    new_documents = [Document(text=text.strip()) for text in texts if text.strip()]
    if not new_documents:
        raise ValueError("No valid texts provided for ingestion.")

    os.makedirs(db_dir, exist_ok=True)

    index = None

    if os.listdir(db_dir):
        try:
            storage_context = StorageContext.from_defaults(persist_dir=db_dir)
            index = load_index_from_storage(storage_context)
        except Exception as e:
            index = None

    if index is None:
        try:
            index = VectorStoreIndex([])
            for doc in new_documents:
                index.insert(doc)
        except Exception as e:
            raise RuntimeError(f"Error creating index from documents: {e}")
    else:
        try:
            for doc in new_documents:
                index.insert(doc) 
        except Exception as e:
            raise RuntimeError(f"Error inserting new documents: {e}")
        
    try:
        index.storage_context.persist(persist_dir=db_dir)
    except Exception as e:
        raise RuntimeError(f"Error persisting index to disk: {e}")

    return {
        "status": "success",
        "message": f"Successfully ingested {len(new_documents)} documents. Updated index persisted to {db_dir}"
    }
