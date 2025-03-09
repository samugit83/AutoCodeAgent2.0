import os
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    SimpleDirectoryReader
)
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceWindowNodeParser
from params import PARAMS

def llama_index_context_window_ingest_corpus():
    """
    Ingest documents from a directory into a LlamaIndex vector store with context window enrichment.
    
    This function:
      - Loads environment variables (including OPENAI_API_KEY) from your environment.
      - Uses SimpleDirectoryReader to load documents from the corpus directory.
      - Applies a SentenceWindowNodeParser (via an IngestionPipeline) to add surrounding context to document chunks.
      - Checks for an existing index in the specified directory and appends new nodes,
        or creates a new index if none exists.
      - Persists the updated index back to disk.
    
    Parameters:
      corpus_dir (str): Directory where the documents are stored.
      db_dir (str): Directory where the index files will be stored.
    
    Returns:
      dict: A status message.
    """
    db_dir = PARAMS["LLAMA_INDEX_CONTEXT_WINDOW_DB_PATH"]
    corpus_dir = PARAMS["LLAMA_INDEX_CONTEXT_WINDOW_CORPUS_DIR"]
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in environment. Check your .env file.")

    # Load documents from the corpus directory.
    try:
        reader = SimpleDirectoryReader(input_dir=corpus_dir)
        documents = reader.load_data()
    except Exception as e:
        raise RuntimeError(f"Error loading documents from corpus: {e}")

    if not documents:
        raise ValueError("No documents loaded from the corpus directory.")

    os.makedirs(db_dir, exist_ok=True)
    window_size = PARAMS["LLAMA_INDEX_CONTEXT_WINDOW_SIZE_INGEST"]

    # Enrich documents with context using SentenceWindowNodeParser.
    try:
        node_parser = SentenceWindowNodeParser(
            window_size=window_size,  # e.g., 3 sentences on each side gives a total window of 7 sentences.
            window_metadata_key="window",
            original_text_metadata_key="original_sentence"
        )
        pipeline = IngestionPipeline(transformations=[node_parser])
        new_nodes = pipeline.run(documents=documents)
    except Exception as e:
        raise RuntimeError(f"Error processing documents with context window pipeline: {e}")

    # Try to load an existing index if possible.
    index = None
    docstore_path = os.path.join(db_dir, "docstore.json")
    if os.path.exists(docstore_path):
        try:
            # Attempt to load the storage context using the persisted directory.
            storage_context = StorageContext.from_defaults(persist_dir=db_dir)
            index = load_index_from_storage(storage_context)
        except Exception:
            # If loading fails, fall back to creating a new context.
            index = None
            storage_context = StorageContext.from_defaults()
            storage_context.persist_dir = db_dir
    else:
        # If the expected file is missing, create a new storage context.
        index = None
        storage_context = StorageContext.from_defaults()
        storage_context.persist_dir = db_dir

    if index is None:
        try:
            # Create a new index by passing the enriched nodes.
            index = VectorStoreIndex(new_nodes, storage_context=storage_context)
        except Exception as e:
            raise RuntimeError(f"Error creating index from documents: {e}")
    else:
        try:
            for node in new_nodes:
                index.insert(node)
        except Exception as e:
            raise RuntimeError(f"Error inserting new nodes: {e}")

    try:
        index.storage_context.persist(persist_dir=db_dir)
    except Exception as e:
        raise RuntimeError(f"Error persisting index to disk: {e}")

    return {
        "status": "success",
        "message": f"Successfully ingested {len(documents)} documents. Updated index persisted to {db_dir}"
    }
