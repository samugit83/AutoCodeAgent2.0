from string import Template

EXTRACT_QUERY_FEATS_PROMPT = Template(
    "Given the following query: '$query', "
    "please extract the following features: question_type, domain, has_entities, complexity, ambiguity, query_length, specificity, formality, and urgency. "
    "Return the result as a JSON array in the format "
    "[question_type, domain, has_entities, complexity, ambiguity, query_length, specificity, formality, urgency].\n\n"
    "For each feature, please adhere to the following guidelines:\n"
    "- question_type: A string representing the type of question. Choose one from the following list: ['fact', 'opinion', 'definition', 'explanation', 'procedure', 'comparison', 'hypothetical', 'evaluation'].\n"
    "- domain: A string indicating the subject domain. Choose one from the following list: ['science', 'technology', 'mathematics', 'history', 'literature', 'geography', 'politics', 'economics', 'sports', 'entertainment', 'health', 'education', 'philosophy', 'art', 'environment', 'law', 'music', 'culture', 'business', 'travel'].\n"
    "- has_entities: A boolean value (true or false) indicating whether the query mentions named entities.\n"
    "- complexity: A float representing the query complexity, with a minimum of 0.0 (simple) and a maximum of 1.0 (complex).\n"
    "- ambiguity: A float representing the query ambiguity, with a minimum of 0.0 (unambiguous) and a maximum of 1.0 (highly ambiguous).\n"
    "- query_length: An integer representing the number of words in the query, with a minimum of 1 and a maximum of 100.\n"
    "- specificity: A float representing how specific the query is, with a minimum of 0.0 (very broad) and a maximum of 1.0 (very specific).\n"
    "- formality: A float representing the formality level of the query, with a minimum of 0.0 (informal) and a maximum of 1.0 (formal).\n"
    "- urgency: A float representing the urgency of the query, with a minimum of 0.0 (not urgent) and a maximum of 1.0 (extremely urgent)."
)


SUGGEST_ACTION_PROMPT = Template(
    "Given the following query: '$query', please determine the most appropriate RAG technique to use. "
    "Select one of the following options by returning its corresponding number only:\n"
    "0: LlamaIndex RAG: Basic implementation of simple retrieval\n"
    "1: HydeRag: In this system, a language model transforms a user’s query into an extensive, hypothetical document. This document then serves as an enriched query to search through a vector space, improving the alignment with the stored documents.\n"
    "2: AdaptiveRAG: Adapts its retrieval strategy based on the query type by classifying queries (e.g., factual, analytical, opinion, contextual) and dynamically selecting the best retrieval method to enhance precision and context-awareness.\n"
    "Return only the number."
)

RAG_ANSWER_PROMPT = Template(
    "Given the following query: '$query', please provide a detailed answer using the following context extracted through RAG: '$context'. "
    "Return only the answer."
)