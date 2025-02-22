from llama_index.core import StorageContext, load_index_from_storage

def retrieve_documents(query, persist_dir="./tools/rag/llama_index/database"):
    """
    Retrieves the most relevant documents from a persisted LlamaIndex index using the provided query.
    
    This function:
      - Loads the persisted LlamaIndex from disk using the given persist directory.
      - Creates a query engine from the loaded index.
      - Executes the query on the index.
    
    Args:
      query (str): The query string to search for.
      persist_dir (str): Directory where the LlamaIndex is persisted.
      
    Returns:  
      str: A string containing the query response. 
    """
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    query_engine = index.as_query_engine()
    response = query_engine.query(query)
    return str(response)

 