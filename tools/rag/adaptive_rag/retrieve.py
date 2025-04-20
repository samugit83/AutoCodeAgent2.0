import logging
import re
from tools.rag.llama_index.retrieve import retrieve_documents
from models.models import call_model
from .prompts import (
    ADAPTIVE_QUERY_CLASSIFIER_PROMPT,
    ADAPTIVE_FACTUAL_ENHANCE_PROMPT,
    ADAPTIVE_FACTUAL_RANK_PROMPT,
    ADAPTIVE_ANALYTICAL_SUBQUERY_PROMPT,
    ADAPTIVE_ANALYTICAL_DIVERSITY_PROMPT,
    ADAPTIVE_OPINION_VIEWPOINTS_PROMPT,
    ADAPTIVE_OPINION_RANK_PROMPT,
    ADAPTIVE_CONTEXTUAL_REFORMULATE_PROMPT,
    ADAPTIVE_CONTEXTUAL_RANK_PROMPT,
    ADAPTIVE_FINAL_ANSWER_PROMPT
)
from params import PARAMS

logger = logging.getLogger(__name__)

class QueryClassifier:
    def __init__(self, model: str):
        self.model = model
    
    def classify(self, query: str) -> str:
        prompt = ADAPTIVE_QUERY_CLASSIFIER_PROMPT.substitute(query=query)
        category = call_model(
            chat_history=[{"role": "user", "content": prompt}],
            model=self.model
        )
        return category


class BaseRetrievalStrategy:
    def __init__(self, model: str):
        self.model = model
        self.top_k = PARAMS["ADAPTIVE_RAG_QUERY_TOP_K"]

class FactualRetrievalStrategy(BaseRetrievalStrategy):
    def __init__(self, model: str):
        super().__init__(model)
    
    def retrieve(self, query: str):
        enhance_prompt = ADAPTIVE_FACTUAL_ENHANCE_PROMPT.substitute(query=query)
        enhanced_response = call_model(
            chat_history=[{"role": "user", "content": enhance_prompt}],
            model=self.model
        )
 
        logger.info("--- Adaptive RAG process --- ✨ Enhanced query: %s", enhanced_response) 
        
        docs = retrieve_documents(enhanced_response, similarity_top_k=self.top_k * 2)
        
        ranked = []
        for doc in docs:
            rank_prompt = ADAPTIVE_FACTUAL_RANK_PROMPT.substitute(
                query=enhanced_response,
                doc=doc
            )
            rank_response = call_model(
                chat_history=[{"role": "user", "content": rank_prompt}],
                model=self.model
            )
            logger.info("Adaptive RAG process: 📚 Ranked response: %s", rank_response)
            try:
                score = float(rank_response)
            except:
                score = 0.0
            ranked.append((doc, score))
        ranked.sort(key=lambda x: x[1], reverse=True)
        selected_docs = [doc for doc, _ in ranked[:self.top_k]]
        return selected_docs


class AnalyticalRetrievalStrategy(BaseRetrievalStrategy):
    def __init__(self, model: str):
        super().__init__(model)
    
    def retrieve(self, query: str):
        subquery_prompt = ADAPTIVE_ANALYTICAL_SUBQUERY_PROMPT.substitute(query=query, k=self.top_k)
        subquery_response = call_model(
            chat_history=[{"role": "user", "content": subquery_prompt}],
            model=self.model
        )

        sub_queries = [sq.strip() for sq in subquery_response.split("\n") if sq.strip()]
        logger.info("--- Adaptive RAG process --- 🔍 Sub-queries: %s", sub_queries)
        
        all_docs = []
        for sub in sub_queries:
            docs = retrieve_documents(sub, similarity_top_k=2)
            all_docs.extend(docs)
        
        docs_text = "\n".join(f"{i}: {doc[:500]}..." for i, doc in enumerate(all_docs))
        diversity_prompt = ADAPTIVE_ANALYTICAL_DIVERSITY_PROMPT.substitute(
            query=query, docs=docs_text, k=self.top_k
        )
        indices_str = call_model(
            chat_history=[{"role": "user", "content": diversity_prompt}],
            model=self.model
        )

        indices = []
        for part in indices_str.split(","):
            try:
                idx = int(part.strip())
                if idx < len(all_docs):
                    indices.append(idx)
            except:
                continue
        selected_docs = [all_docs[i] for i in indices]
        return selected_docs


class OpinionRetrievalStrategy(BaseRetrievalStrategy):
    def __init__(self, model: str):
        super().__init__(model)
    
    def retrieve(self, query: str):
        viewpoints_prompt = ADAPTIVE_OPINION_VIEWPOINTS_PROMPT.substitute(query=query, k=self.top_k)
        viewpoints_response = call_model(
            chat_history=[{"role": "user", "content": viewpoints_prompt}],
            model=self.model
        )
        viewpoints = [v.strip() for v in viewpoints_response.split("\n") if v.strip()]
        logger.info("--- Adaptive RAG process --- 👀 Viewpoints: %s", viewpoints)
        
        all_docs = []
        for viewpoint in viewpoints:
            docs = retrieve_documents(query + " " + viewpoint, similarity_top_k=2)
            all_docs.extend(docs)
        
        docs_text = "\n".join(f"{i}: {doc[:50]}..." for i, doc in enumerate(all_docs))
        opinion_prompt = ADAPTIVE_OPINION_RANK_PROMPT.substitute(
            query=query, docs=docs_text, k=self.top_k
        )
        opinion_response = call_model(
            chat_history=[{"role": "user", "content": opinion_prompt}],
            model=self.model
        )

        indices = []
        for part in opinion_response.split(","):
            try:
                idx = int(part.strip())
                if idx < len(all_docs):
                    indices.append(idx)
            except:
                continue
        selected_docs = [all_docs[i] for i in indices]
        return selected_docs


class ContextualRetrievalStrategy(BaseRetrievalStrategy):
    def __init__(self, model: str):
        super().__init__(model)
        self.extracted_context = "No specific context provided" 
    
    def retrieve(self, query: str, user_context: str = None):
        context_to_use = user_context or self.extracted_context
        reformulate_prompt = ADAPTIVE_CONTEXTUAL_REFORMULATE_PROMPT.substitute(query=query, context=context_to_use)
        reformulated_response = call_model(
            chat_history=[{"role": "user", "content": reformulate_prompt}],
            model=self.model
        )
        
        logger.info("--- Adaptive RAG process --- 🔄 Reformulated query: %s", reformulated_response)
        
        docs = retrieve_documents(reformulated_response, similarity_top_k=self.top_k * 2)

        ranked = []
        for doc in docs:
            rank_prompt = ADAPTIVE_CONTEXTUAL_RANK_PROMPT.substitute(
                query=reformulated_response,
                context=context_to_use,
                doc=doc
            )
            rank_response = call_model(
                chat_history=[{"role": "user", "content": rank_prompt}],
                model=self.model
            )
            try:
                score = float(rank_response)
            except:
                score = 0.0
            ranked.append((doc, score))
        ranked.sort(key=lambda x: x[1], reverse=True)
        selected_docs = [doc for doc, _ in ranked[:self.top_k]]
        return selected_docs


class AdaptiveRetriever:
    def __init__(self, model: str):
        self.classifier = QueryClassifier(model)
        self.strategies = {
            "Factual": FactualRetrievalStrategy(model),
            "Analytical": AnalyticalRetrievalStrategy(model),
            "Opinion": OpinionRetrievalStrategy(model),
            "Contextual": ContextualRetrievalStrategy(model)
        }
    
    def get_relevant_documents(self, query: str, user_context: str = None):
        classifier_output = self.classifier.classify(query)
        logger.info("--- Adaptive RAG process --- 🎯 Selected strategy: %s", classifier_output)
        
        if classifier_output.startswith("Contextual"):
            match = re.search(r"<context>(.*?)</context>", classifier_output) 
            if match:
                extracted_context = match.group(1).strip()
                logger.info("--- Adaptive RAG process --- ⛏️ Extracted context from user query: %s", extracted_context)
            else:
                extracted_context = user_context or "No specific context provided"
            self.strategies["Contextual"].extracted_context = extracted_context 
            strategy = self.strategies.get("Contextual")
            return strategy.retrieve(query, user_context=extracted_context)
        else:
            category = classifier_output.strip()
            strategy = self.strategies.get(category, FactualRetrievalStrategy(self.classifier.model))
            return strategy.retrieve(query)

class AdaptiveRAG:
    def __init__(self):
        self.model = PARAMS["ADAPTIVE_RAG_MODEL"]
        self.retriever = AdaptiveRetriever(self.model)
    
    def answer(self, query: str, user_context: str = None) -> str:
        docs_string = self.retriever.get_relevant_documents(query, user_context)

        final_prompt = ADAPTIVE_FINAL_ANSWER_PROMPT.substitute(context=docs_string, question=query)
        answer_response = call_model(
            chat_history=[{"role": "user", "content": final_prompt}],
            model=self.model
        )
        return answer_response
