PARAMS = {
    # Simple RAG parameters
    "SIMPLE_RAG_CHUNK_SIZE": 1500,  # Size of text chunks for simple RAG processing
    "SIMPLE_RAG_OVERLAP": 200,  # Overlap between chunks to maintain context
    "SIMPLE_RAG_EMBEDDING_MODEL": "text-embedding-ada-002",  # Model used for creating embeddings in simple RAG
    
    # Hybrid Vector Graph RAG parameters
    "HYBRID_VECTOR_GRAPH_RAG_CHUNK_SIZE": 1500,  # Size of text chunks for hybrid vector-graph RAG
    "HYBRID_VECTOR_GRAPH_RAG_OVERLAP": 200,  # Overlap between chunks in hybrid RAG
    "HYBRID_VECTOR_GRAPH_RAG_SUMMARIZATION_GRAPH_NODE_LENGTH": 100,  # Length of summarized content in graph nodes
    "HYBRID_VECTOR_GRAPH_RAG_SIMILARITY_RETRIEVE_THRESHOLD": 0.9,  # Threshold for retrieving similar chunks
    "HYBRID_VECTOR_GRAPH_RAG_SIMILARITY_EDGE_THRESHOLD": 0.9,  # Threshold for creating edges between similar chunks
    "HYBRID_VECTOR_GRAPH_RAG_QUERY_MAX_DEPTH": 3,  # Maximum depth for graph traversal during queries
    "HYBRID_VECTOR_GRAPH_RAG_QUERY_TOP_K": 3,  # Number of top results to return in hybrid RAG queries
    "HYBRID_VECTOR_GRAPH_RAG_QUERY_MAX_CONTEXT_LENGTH": 10000,  # Maximum context length for hybrid RAG queries
    "HYBRID_VECTOR_GRAPH_RAG_EMBEDDING_VECTOR_MODEL": "text-embedding-ada-002",  # Model for vector embeddings, use only open ai embedding service
    "HYBRID_VECTOR_GRAPH_RAG_SUMMARIZATION_GRAPH_NODE_MODEL": "gpt-4o",  # Model for summarizing graph nodes
    
    # Database paths
    "CHROMA_DB_PATH": "./tools/rag/database/chroma_db",  # Path to ChromaDB used in simple RAG
    "LLAMA_INDEX_DB_PATH": "./tools/rag/database/llama_index",  # Path for LlamaIndex database
    "LLAMA_INDEX_CONTEXT_WINDOW_DB_PATH": "./tools/rag/database/llama_index_context_window",  # Path for LlamaIndex context window database
    
    # Llama Index parameters
    "LLAMA_INDEX_TOP_K_RAG_RETRIEVE": 5,  # Number of top results to retrieve in LlamaIndex RAG
    "LLAMA_INDEX_CORPUS_DIR": "./tools/rag/llama_index/corpus",  # Directory for LlamaIndex corpus
    "LLAMA_INDEX_CONTEXT_WINDOW_CORPUS_DIR": "./tools/rag/llama_index_context_window/corpus",  # Directory for LlamaIndex context window corpus
    "LLAMA_INDEX_CONTEXT_WINDOW_SIZE_INGEST": 30,  # Number of sentences for context window ingestion
    "LLAMA_INDEX_CONTEXT_WINDOW_MAX_ADJACENT_CHARS_RAG_RETRIEVE": 150,  # Maximum adjacent characters for context window retrieval
    "LLAMA_INDEX_CONTEXT_WINDOW_TOP_K_RAG_RETRIEVE": 5,  # Number of top chunks to retrieve in context window RAG
    
    # HyDE RAG parameters
    "HYDE_RAG_CHUNK_SIZE": 1500,  # Size of chunks for HyDE RAG processing
    "HYDE_RAG_QUERY_TOP_K": 5,  # Number of top results to return in HyDE RAG queries
    "HYDE_GENERATE_HYPO_DOC_MODEL": "gpt-4o",  # Model used for generating hypothetical documents in HyDE
    
    # Adaptive RAG parameters
    "ADAPTIVE_RAG_MODEL": "gpt-4o",  # Model used for adaptive RAG processing
    "ADAPTIVE_RAG_QUERY_TOP_K": 5,  # Number of top results to return in adaptive RAG queries

    # RL Meta RAG defaults
    "RAG_Q_DATA_FILE": "tools/rag/rl_meta_rag/rag_q_data.pkl",  # Filename used to persist Q-learning data (e.g., stored as a pickle file)
    "RL_N_RECENT": 50,                   # Number of recent episodes considered when computing the average prediction error
    "RL_ERROR_THRESHOLD": 0.5,           # Error threshold above which the system may fall back to LLM suggestions instead of relying on Q-learning
    "RL_ALPHA": 0.8,                     # Learning rate for Q-learning; controls how quickly new information overrides old Q-values
    "RL_GAMMA": 0.95,                    # Discount factor for Q-learning; determines the importance of future rewards compared to immediate rewards
    "RL_EPSILON": 0.1,                   # Exploration rate for epsilon-greedy strategy; probability of choosing a random action versus the best-known action
    "RL_META_RAG_MODEL": "gpt-4o",       # Model used for RL Meta RAG
    "RL_REQUEST_HUMAN_EVALUATION": True, # Model used for request evaluation
    
    # Intellichain parameters
    "MAX_ITERATIONS_AFTER_EVALUATION": 1,  # Maximum number of iterations after not satisfactory evaluation
    "TOOL_HELPER_MODEL": "gpt-4o",  # Model used for default tool helper_model
    "TOOL_HELPER_MODEL_WEB_SEARCH": "gpt-4o-search-preview",  # Model used for default tool helper_model_with_web_search, only 2 values are allowed: gpt-4o-search-preview or gpt-4o-mini-search-preview
    "JSON_PLAN_MODEL": "gpt-4o",  # Model used for JSON planning
    "EVALUATION_MODEL": "gpt-4o",  # Model used for evaluation tasks
    "SURF_AI_JSON_TASK_MODEL": "gpt-4o",  # Model for SurfAI JSON tasks (requires multimodal capabilities)

    "CUA_FIRST_URL_MODEL": "gpt-4o",  # Model used to generate the first url for CUA 

    # Deep Search parameters
    "DEEP_SEARCH_MODEL": "o3-mini",  # Model used for deep search functionality

    "APPLY_MODEL_OPTIONS": True, # Apply options to the model, from the /models/models_options.py file
} 