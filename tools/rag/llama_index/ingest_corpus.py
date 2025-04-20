import os
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    SimpleDirectoryReader
)
from params import PARAMS

def llama_index_ingest_corpus():
    """
    Ingest documents from a directory into a LlamaIndex vector store.
    
    This function:
      - Loads environment variables (including OPENAI_API_KEY) from your environment.
      - Instantiates an OpenAI embedding model.
      - Uses SimpleDirectoryReader to load documents from the corpus directory.
      - Checks for an existing index in the specified directory and appends new documents,
        or creates a new index if none exists.
      - Persists the updated index back to disk using the storage_context.persist() method.
    
    Parameters:
      corpus_dir (str): Directory where the documents are stored.
      db_dir (str): Directory where the index files will be stored.
    
    Returns:
      dict: A status message.
    """
    corpus_dir = PARAMS["LLAMA_INDEX_CORPUS_DIR"]
    db_dir = PARAMS["LLAMA_INDEX_DB_PATH"]
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in environment. Check your .env file.")

    try:
        reader = SimpleDirectoryReader(input_dir=corpus_dir)
        documents = reader.load_data()
    except Exception as e:
        raise RuntimeError(f"Error loading documents from corpus: {e}")

    if not documents:
        raise ValueError("No documents loaded from the corpus directory.")

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
            for doc in documents:
                index.insert(doc)
        except Exception as e:
            raise RuntimeError(f"Error creating index from documents: {e}")
    else:
        try:
            for doc in documents:
                index.insert(doc)
        except Exception as e:
            raise RuntimeError(f"Error inserting new documents: {e}")

    try:
        index.storage_context.persist(persist_dir=db_dir)
    except Exception as e:
        raise RuntimeError(f"Error persisting index to disk: {e}")

    return {
        "status": "success",
        "message": f"Successfully ingested {len(documents)} documents. Updated index persisted to {db_dir}"
    }
