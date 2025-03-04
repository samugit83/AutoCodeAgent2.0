import os
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor

import logging

logger = logging.getLogger(__name__)

def retrieve_documents(query, similarity_cutoff=None):
    """
    Retrieves the most relevant documents from a persisted LlamaIndex index using the provided query.
    
    This function:
      - Loads the persisted LlamaIndex from disk using the given persist directory. 
      - Configures a retriever with a default top-k (similarity_top_k) of 5.
      - Optionally applies a node postprocessor with a similarity cutoff if provided.
      - Sets up a default response synthesizer.
      - Creates a custom query engine combining these components.
      - Executes the query on the index.
    
    Args:
      query (str): The query string to search for.
      persist_dir (str): Directory where the LlamaIndex is persisted.
      similarity_top_k (int, optional): Number of top documents to retrieve. Defaults to 5.
      similarity_cutoff (float, optional): Minimum similarity score to filter nodes. If None, no filtering is applied.
      
    Returns:  
      str: A string representation of the retrieved documents.
    """
    similarity_top_k = int(os.getenv("LLAMA_INDEX_TOP_K_RAG_RETRIEVE", '5'))
    persist_dir = os.getenv("LLAMA_INDEX_DB_PATH")
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=similarity_top_k,
    )
    node_postprocessors = []

    if similarity_cutoff is not None:
        node_postprocessors.append(SimilarityPostprocessor(similarity_cutoff=similarity_cutoff))
    

    retrieved_nodes = retriever.retrieve(query)
    
    texts = []
    for node_obj in retrieved_nodes:
        if hasattr(node_obj, "node") and hasattr(node_obj.node, "text"):
            texts.append(node_obj.node.text)
        elif isinstance(node_obj, dict) and "text" in node_obj:
            texts.append(node_obj["text"])
        else:
            texts.append(str(node_obj))
    
    return texts

