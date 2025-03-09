import logging
import os
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.postprocessor import SimilarityPostprocessor, MetadataReplacementPostProcessor
from params import PARAMS

logger = logging.getLogger(__name__)

class CustomMetadataReplacementPostProcessor(MetadataReplacementPostProcessor):
    def __init__(self, target_metadata_key: str):
        super().__init__(target_metadata_key=target_metadata_key)

    def process(self, node, **kwargs):
        """
        Reconstruct the context from the node metadata. If the node has an "original_sentence"
        in its metadata, locate that sentence within the window (kept as a raw string) and extend it
        by including up to max_adjacent_chars before and after the original sentence. Otherwise, return
        the original full text.
        """
 
        max_adjacent_chars = PARAMS["LLAMA_INDEX_CONTEXT_WINDOW_MAX_ADJACENT_CHARS_RAG_RETRIEVE"]
        full_text = getattr(node, "text", "")
        window_data = node.metadata.get(self.target_metadata_key)
        original_sentence = node.metadata.get("original_sentence")
        
        if window_data:
            window_data = window_data.strip()
             
            if original_sentence:
                index = window_data.find(original_sentence)
                if index == -1:
                    logger.info("Llama index process: 🔴 Original chunk not found; returning entire window data.")
                    return window_data
                else:
                    start = max(0, index - max_adjacent_chars)
                    end = min(len(window_data), index + len(original_sentence) + max_adjacent_chars)
                    trimmed = window_data[start:end]
                    logger.info(f"Llama index process: ✅ Found original chunk with length: {len(original_sentence)} at index: {index} and end at index: {index + len(original_sentence)}")
                    logger.info(f"Updated chunk has final length >>>>>> {len(trimmed)} <<<<<<")
                    return trimmed
            else:
                logger.info("Llama index process: 🔴 No original sentence found; returning full window data.")
                return window_data
        return full_text

def retrieve_documents(query, similarity_cutoff=None):
    similarity_top_k = PARAMS["LLAMA_INDEX_CONTEXT_WINDOW_TOP_K_RAG_RETRIEVE"]
    persist_dir = PARAMS["LLAMA_INDEX_CONTEXT_WINDOW_DB_PATH"]
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    
    # Configure postprocessors:
    node_postprocessors = [
        CustomMetadataReplacementPostProcessor(target_metadata_key="window")
    ]
    if similarity_cutoff is not None:
        node_postprocessors.append(SimilarityPostprocessor(similarity_cutoff=similarity_cutoff))
    
    query_engine = index.as_query_engine(
        similarity_top_k=similarity_top_k,
        node_postprocessors=node_postprocessors
    )
    
    response = query_engine.query(query)
    retrieved_nodes = response.source_nodes
    
    custom_postprocessor = CustomMetadataReplacementPostProcessor(target_metadata_key="window")
    
    texts = []
    for node_obj in retrieved_nodes:
        if hasattr(node_obj, "node") and hasattr(node_obj.node, "text"):
            processed_text = custom_postprocessor.process(node_obj.node)
            texts.append(processed_text)
        elif isinstance(node_obj, dict) and "text" in node_obj:
            texts.append(node_obj["text"])
        else:
            texts.append(str(node_obj))
    
    return texts
