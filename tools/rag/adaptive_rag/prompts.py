from string import Template


ADAPTIVE_QUERY_CLASSIFIER_PROMPT = Template("""
    Classify the following query into one of the following categories: Factual, Analytical, Opinion, or Contextual.
    If the query is classified as Contextual, output in the following format:
    Contextual<context>here the context extracted from the query</context>
    Otherwise, output only one word from the options (without any additional text): Factual, Analytical, or Opinion.
    Query: $query
""") 

ADAPTIVE_FACTUAL_ENHANCE_PROMPT = Template(
    "Enhance this factual query for better retrieval: $query"
)  

ADAPTIVE_FACTUAL_RANK_PROMPT = Template(
    """On a scale of 1-10, rate the relevance of the following document to the query.
Query: '$query'
Document: $doc
Output only a single integer between 1 and 10 (without any additional text):"""
)

ADAPTIVE_ANALYTICAL_SUBQUERY_PROMPT = Template(
    """Generate exactly $k sub-questions for a comprehensive analysis of the query below.
Query: $query
Output exactly $k sub-questions, each on a separate line, with no additional commentary."""
)

ADAPTIVE_ANALYTICAL_DIVERSITY_PROMPT = Template(
    """From the list of documents below, select exactly $k indices corresponding to the most diverse and relevant documents for the query.
Query: '$query'
Documents:
$docs
Output exactly $k indices as a comma-separated list (e.g., 0,2,4) without any extra text."""
)


ADAPTIVE_OPINION_VIEWPOINTS_PROMPT = Template(
    """Identify exactly $k distinct viewpoints or perspectives on the following topic.
Query: $query
Output exactly $k viewpoints, each on a separate line, with no extra text."""
)

ADAPTIVE_OPINION_RANK_PROMPT = Template(
    """From the list of documents below, select exactly $k indices that correspond to the most representative and diverse opinions for the query.
Query: '$query'
Documents:
$docs
Output exactly $k indices as a comma-separated list (e.g., 0,1,2) without any additional text."""
)

ADAPTIVE_CONTEXTUAL_REFORMULATE_PROMPT = Template(
    "Given the user context: '$context', reformulate the query to best address the user's needs: $query"
)

ADAPTIVE_CONTEXTUAL_RANK_PROMPT = Template(
    """Given the query: '$query' and user context: '$context', rate the relevance of the following document on a scale of 1-10.
Document: $doc
Output exactly one number (an integer between 1 and 10) as the relevance score, with no additional text."""
)


ADAPTIVE_FINAL_ANSWER_PROMPT = Template(
    """Use the following context to answer the question.
Context:
$context

Question: 
$question
Answer:"""
)
