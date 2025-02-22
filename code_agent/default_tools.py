DEFAULT_TOOLS = [
    {
        "tool_name": "helper_model",
        "lib_names": ["models.models"],
        "instructions": "An LLM useful to elaborate any output from previous steps. Don't create loops, just use the LLM to elaborate the output for a single step.",
        "use_exactly_code_example": True,
        "code_example": """
def call_helper_model(previous_output):
    from models.models import call_model
    try:
        updated_dict = previous_output.copy()

        message = updated_dict.get('message', '')
        if len(message) > 350000:
            message: str = message[:350000]
        updated_dict['message'] = message
        
        prompt = f"here you describe how to elaborate the previous output: {updated_dict.get('message','')}"
        llm_response: str = call_model(
            chat_history=[{"role": "user", "content": prompt}],
            model="$TOOL_HELPER_MODEL"
        )
        updated_dict["elaborated_output"] = llm_response
        return updated_dict
    except Exception as e:
        logger.error(f"Error calling helper model: {e}")
        return previous_output
"""
    },
    {
        "tool_name": "ingest_simple_rag",
        "lib_names": ["tools.rag.simple_rag.ingest"],
        "instructions": "This is a simple RAG ingestion tool. Ingest the text into the vector database.",
        "use_exactly_code_example": True,
        "code_example": """
def ingest_rag_db(previous_output):
    from tools.rag.simple_rag.ingest import ingest_texts
    try:
        updated_dict = previous_output.copy()
        
        text: str = updated_dict.get("text", "")
        ingest_result: dict = ingest_texts([text], model="$SIMPLE_RAG_EMBEDDING_MODEL")
        updated_dict["ingest_result"] = str(ingest_result)
        return updated_dict
    except Exception as e:
        logger.error(f"Error ingesting texts: {e}")
        return previous_output
"""
    },
    {
        "tool_name": "retrieve_simple_rag",
        "lib_names": ["tools.rag.simple_rag.retrieve"],
        "instructions": ("This is a simple RAG extraction tool. Extract only the information and provide a straightforward response "
                         "with the acquired information. Do not create additional tools unless necessary. Retrieve the text from the vector database."),
        "use_exactly_code_example": True,
        "code_example": """
def retrieve_rag_db(previous_output):
    try:
        from tools.rag.simple_rag.retrieve import retrieve_documents 
        updated_dict = previous_output.copy()
        
        query = updated_dict.get("query", "")
        retrieve_result: dict = retrieve_documents(query, model="$SIMPLE_RAG_EMBEDDING_MODEL")
        updated_dict["retrieve_result"] = str(retrieve_result)
        return updated_dict
    except Exception as e:
        logger.error(f"Error extracting documents: {e}")
        return previous_output
"""
    }, 
    {
        "tool_name": "ingest_hybrid_vector_graph_rag",
        "lib_names": ["tools.rag.hybrid_vector_graph_rag.engine"],
        "instructions": "This is an Hybrid Vector Graph RAG ingestion tool. Ingest the text into the vector and graph database.",
        "use_exactly_code_example": True,
        "code_example": """
def ingest_hybrid_vector_graph_rag_db(previous_output):
    from tools.rag.hybrid_vector_graph_rag.engine import HybridVectorGraphRag
    try:
        updated_dict = previous_output.copy()
        
        engine = HybridVectorGraphRag()
        text: str = updated_dict.get("text", "")
        ingest_result: dict = engine.ingest([text])
        updated_dict["ingest_result"] = str(ingest_result)
        return updated_dict
    except Exception as e:
        logger.error(f"Error ingesting texts: {e}")
        return previous_output
"""
    },
    {
        "tool_name": "retrieve_hybrid_vector_graph_rag",
        "lib_names": ["tools.rag.hybrid_vector_graph_rag.engine"],
        "instructions": ("This is an Hybrid Vector Graph RAG extraction tool. Extract only the information and provide a straightforward response "
                         "with the acquired information. Do not create additional tools unless necessary. Retrieve the text from the vector database. "
                         "Activate this tool when the client explicitly requests to retrieve the text from a database."),
        "use_exactly_code_example": True,
        "code_example": """
def retrieve_hybrid_vector_graph_rag_db(previous_output):
    from tools.rag.hybrid_vector_graph_rag.engine import HybridVectorGraphRag
    try:
        updated_dict = previous_output.copy() 
        
        engine = HybridVectorGraphRag()
        question: str = updated_dict.get("query", "")
        result: dict = engine.retrieve(question)
        updated_dict["retrieve_result"] = str(result)
        return updated_dict
    except Exception as e:
        logger.error(f"Error extracting documents: {e}")
        return previous_output
"""
    },
    {
    "tool_name": "ingest_llama_index",
    "lib_names": ["tools.rag.llama_index.ingest"],
    "instructions": "This tool ingests text into the LlamaIndex vector database.",
    "use_exactly_code_example": True,
    "code_example": """
def ingest_llama_index(previous_output): 
    from tools.rag.llama_index.ingest import ingest_texts
    try:
        updated_dict = previous_output.copy()
        text: str = updated_dict.get("text", "")
        if not text:
            return updated_dict

        # Call the function with the text wrapped in a list.
        result: dict = ingest_texts([text])
        updated_dict["ingest_result"] = str(result)
        return updated_dict
    except Exception as e:
        logger.error(f"Error in ingest_llama_index: {e}") 
        return previous_output
"""
    },
    {
    "tool_name": "retrieve_llama_index",
    "lib_names": ["tools.rag.llama_index.retrieve"],
    "instructions": ("This tool retrieves documents from a persisted LlamaIndex index."),
    "use_exactly_code_example": True,
    "code_example": """
def retrieve_llama_index(previous_output):
    from tools.rag.llama_index.retrieve import retrieve_documents
    try:
        updated_dict = previous_output.copy()
        query: str = updated_dict.get("query", "")
        if not query:
            return updated_dict 
        
        result: str = retrieve_documents(query) 
        updated_dict["retrieve_result"] = result
        return updated_dict
    except Exception as e:
        logger.error(f"Error in retrieve_llama_index: {e}")
        return previous_output 
"""
    }, 
    { 
        "tool_name": "search_web",
        "lib_names": ["duckduckgo_search", "bs4", "requests"],
        "instructions": ("A library to scrape the web. Never use the regex or other specific method to extract the data, always output the whole page. "
                         "The data must be extracted or summarized from the page using the models library. Never perform searches in a loop, if you need to make more research, create a new subtask."),
        "use_exactly_code_example": True,
        "code_example": """
def search_web(previous_output, max_results=3, max_chars=10000):
    from duckduckgo_search import DDGS
    import requests
    from bs4 import BeautifulSoup

    try:
        updated_dict = previous_output.copy()
        
        query: str = updated_dict.get("query", "")
        ddgs = DDGS()
        results = ddgs.text(query, max_results=max_results)
        
        successful_hrefs = []
        full_text_output = [] 

        for result in results:
            href = result.get("href", "")
            if not href:
                # Skip if there's no link
                continue

            try:
                resp = requests.get(href, timeout=10)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, 'html.parser')
                text_content: str = soup.get_text(separator=' ', strip=True)

                limited_text: str = text_content[:max_chars]

                title: str = result.get("title", "")
                full_text_output.append(
                    f"=== START OF ARTICLE ==="
                    f"Title: {title} URL: {href}"
                    f"{limited_text}"
                    f"=== END OF ARTICLE ==="
                )

                successful_hrefs.append(href)

            except Exception as fetch_err:
                logger.error(f"Error fetching page {href}: {fetch_err}") 
                continue

        logger.info(f"Retrieved {len(successful_hrefs)} pages. URLs: {successful_hrefs}")
        html_content: str = " ".join(full_text_output)
        updated_dict["html_content"] = html_content
        return updated_dict
    except Exception as e:
        logger.error(f"Error in search_web: {e}")
        return previous_output
"""
    },
    {
        "tool_name": "browser_navigation",  
        "lib_names": ["tools.surf_ai.engine"],
        "instructions": ("This is an agent that automates browser navigation. Use it to interact with the browser and extract data during navigation.\n"
                         "From the original prompt, reformulate it with input containing only the instructions for navigation, vision capablity and text data extraction.\n"
                         "It also has visual capabilities, so it can be used to analyze the graphics of the web page and images.\n"
                         "For example: \n"
                         "Initial user prompt: use the browser navigator to go to Wikipedia, search for Elon Musk, extract all the information from the page, and analyze with your vision capability his image, and send a summary of the extracted information via email to someone@example.com\n"
                         "Input prompt for browser navigation: go to Wikipedia, search for Elon Musk, extract all the information from the page, and analyze with your vision capability his image.\n"
                         "**Never forget important instructions on navigation and data extraction.**"),
        "use_exactly_code_example": True,
        "code_example": """
def browser_navigation(previous_output):
    from tools.surf_ai.engine import SurfAiEngine 
    try:
        updated_dict = previous_output.copy()
        
        prompt: str = updated_dict.get("prompt", "")
        surf_ai_engine = SurfAiEngine() 
        final_answer_message: str = surf_ai_engine.go_surf(prompt)
        updated_dict["result"] = final_answer_message
        return updated_dict
    except Exception as e:
        logger.error(f"Error browser navigation: {e}")
        return previous_output
"""
    },
    {
        "tool_name": "send_email",
        "lib_names": ["smtplib", "email"],
        "instructions": "Send an email to the user with the given email, subject and html content.",
        "use_exactly_code_example": True,
        "code_example": """
def send_email(previous_output) -> dict:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Gmail credentials
    usermail = $GMAILUSER
    passgmailapp = $PASSGMAILAPP

    # SMTP server configuration
    smtp_server = "smtp.gmail.com"
    port = 587  # For TLS encryption

    try:
        updated_dict = previous_output.copy()

        # Create the email message
        message = MIMEMultipart()
        message["From"] = usermail
        message["To"] = updated_dict.get("email", "")
        message["Subject"] = updated_dict.get("subject", "") 

        # Attach the HTML content
        html_content: str = updated_dict.get("html", "")
        if html_content:
            message.attach(MIMEText(html_content, "html"))

        # Establish connection to the SMTP server
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()  # Secure the connection
            server.login(usermail, passgmailapp)  # Log in to the SMTP server
            
            # Send the email
            server.sendmail(usermail, updated_dict.get("email", ""), message.as_string())
            logger.info(f"Email sent to {updated_dict.get('email', '')} with subject {updated_dict.get('subject', '')}")

        updated_dict["info"] = "Email sent successfully"
        return updated_dict
    except Exception as error:
        logger.error(f"Error sending email: {error}")
        return previous_output
"""
    }
]
