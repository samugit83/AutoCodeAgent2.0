from string import Template

HYDE_DOCS_PROMPT = Template("""
You are a knowledgeable assistant tasked with generating a comprehensive hypothetical document. Given the query "$query", create a detailed and structured document that directly answers the question. Your document must:
- Be exactly $chunk_size characters long.
- Provide an in-depth explanation that bridges the semantic gap between the short query and the longer document representations.
Output only the final text, without any additional commentary.
""")