from llama_index.core import StorageContext, load_index_from_storage, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor

def retrieve_documents(query, persist_dir="./tools/rag/llama_index/database", similarity_top_k=5, similarity_cutoff=None):
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
      str: A string containing the query response.
    """
    # Load persisted index
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    
    # Configure retriever with the provided similarity_top_k
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=similarity_top_k,
    )
    
    # Set up the default response synthesizer
    response_synthesizer = get_response_synthesizer()
    
    # Optionally set up node postprocessors if similarity_cutoff is provided
    node_postprocessors = []
    if similarity_cutoff is not None:
        node_postprocessors.append(SimilarityPostprocessor(similarity_cutoff=similarity_cutoff))
    
    # Assemble the custom query engine integrating retrieval, optional postprocessing, and response synthesis
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
        node_postprocessors=node_postprocessors,
    )
    
    # Execute the query and return the response as a string
    response = query_engine.query(query)
    return str(response)
