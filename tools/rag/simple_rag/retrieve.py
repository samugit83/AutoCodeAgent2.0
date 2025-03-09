import chromadb
from models.models import create_embeddings
from params import PARAMS

def retrieve_documents(query, k=5):
    """
    Retrieves the top-k most similar documents from the specified Chroma collection based on the query,
    using OpenAI embeddings and a persistent Chroma client.
    
    Args:
        query (str): The query string to search for.
        k (int): Number of top similar documents to retrieve.
        collection_name (str, optional): Name of the collection to query. Defaults to "simple_rag" if not provided.
        
    Returns:
        dict: A dictionary containing retrieved documents and their metadata.
    """

    # Use the CHROMA_DB_PATH from environment or default to .chroma
    db_path = PARAMS["CHROMA_DB_PATH"] or ".chroma"
    model = PARAMS["SIMPLE_RAG_EMBEDDING_MODEL"]
    
    collection_name = "simple_rag"

    # Initialize a persistent Chroma client
    try:
        client = chromadb.PersistentClient(path=db_path)
    except TypeError as e:
        raise RuntimeError(f"Error initializing Chroma client: {e}")

    # Access the specified collection or create it if it doesn't exist
    collection = client.get_or_create_collection(name=collection_name)

    query_embedding = create_embeddings([query], model=model)
    query_embedding = [query_embedding[0]]

    # Query the collection for similar documents
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas"]
    )

    return results
