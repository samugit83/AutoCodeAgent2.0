import os
from tools.rag.llama_index.retrieve import retrieve_documents
from models.models import call_model
from .prompts import HYDE_DOCS_PROMPT
from params import PARAMS
import logging

logger = logging.getLogger(__name__)

def generate_hypothetical_document(query):
    chunk_size = PARAMS["HYDE_RAG_CHUNK_SIZE"]
    model = PARAMS["HYDE_GENERATE_HYPO_DOC_MODEL"]

    hyde_doc_prompt = HYDE_DOCS_PROMPT.substitute(  
        query=query,
        chunk_size=chunk_size
    )

    hyde_doc = call_model(
        chat_history=[{"role": "user", "content": hyde_doc_prompt}], 
        model=model
    )

    return hyde_doc

def retrieve_hyde_documents(query):
    hyde_doc = generate_hypothetical_document(query)
    top_k = PARAMS["HYDE_RAG_QUERY_TOP_K"]
    results = retrieve_documents(hyde_doc, similarity_top_k=top_k)
    result_string = "\n".join(results)

    return result_string
  