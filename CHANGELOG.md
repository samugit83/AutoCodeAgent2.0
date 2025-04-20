# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-02-09
- initial release

## [1.1.0] - 2025-02-09
### Added
- Added integration of SurfAi agent for browser automation as a default tool
- Improved the logging system.
- Refactored the core code in `code_agent.py`.
- Updated the prompt with more effective instructions for code generation.
- Modified the parameters passed between various functions to a dynamic dictionary, allowing data transfer in the flow even between non-sequential functions.
- Added the `<finalAnswerDataLog>` tag for data extraction and writing in memory logs, enhancing the management of more complex tasks.
- General improvements in error handling.

## [1.2.0] - 2025-02-11
### Added
- **Function Validator:**  
  - Introduced a comprehensive function validator that leverages Python's `ast` module to analyze and verify function code before execution.  
  - The validator performs multiple checks including:
    - **Syntax Validation:** Ensures the code is syntactically correct.
    - **Import Restrictions:** Verifies that only allowed libraries are imported and disallows relative (local) imports.
    - **Parameter Signature Checks:** Validates that function definitions adhere to expected parameter rules (e.g., no varargs, proper defaults for keyword-only arguments, and correct naming for subtask-specific parameters).
    - **Assignment Verification:** Confirms the presence of mandatory assignments like `updated_dict = previous_output.copy()` for subtasks with index > 0.
    - **Undefined Name Detection:** Identifies any use of undefined names within the function.
    - **Nesting Depth Control:** Ensures function nesting does not exceed one level (primary function plus optional helper functions).
    - **Dangerous Function Call Prevention:** Blocks execution of dangerous functions (e.g., `eval`, `exec`, `compile`, `__import__`, `os.system`, etc.).
    - **updated_dict.get Key Validation:** Checks that keys used in `updated_dict.get(...)` calls exist in the provided `previous_output`.
  - Upon successful validation, the function is automatically renamed to match the expected subtask name.  
- **RAG Llama Index Integration:**  
  - Added capabilities for llama index retrieval and ingest, expanding the system's data ingestion and search functionality.
- **Subtask Regeneration Function:**  
  - Implemented a new function that automatically regenerates a subtask if:
    - The function validator fails during pre-execution checks, or
    - An error is encountered during execution.


## [1.3.0] - 2025-02-15
### Added
- **LangChain Toolbox Integration:**  
  - Integrated LangChain's toolbox, enabling direct access to over 130 tools simply by specifying the tool name.
  - Users can now leverage the extensive list of available tools, streamlining the process of incorporating new functionalities.
  - For a complete list of tools, refer to [LangChain Tools Documentation](https://python.langchain.com/docs/integrations/tools/).

- **Llama Index Corpus Ingestion:**  
  - Integrated capabilities for ingesting data into the llama indexvector database, parsing any file inside the `tools/rag/llama_index/corpus` folder.
  - It can ingest the following file types:
    - `.csv`: Comma-Separated Values
    - `.docx`: Microsoft Word
    - `.epub`: EPUB eBook format
    - `.hwp`: Hangul Word Processor
    - `.ipynb`: Jupyter Notebook
    - `.jpeg`, `.jpg`: JPEG image
    - `.mbox`: MBOX email archive
    - `.md`: Markdown
    - `.mp3`, `.mp4`: Audio and video
    - `.pdf`: Portable Document Format
    - `.png`: Portable Network Graphics
    - `.ppt`, `.pptm`, `.pptx`: Microsoft PowerPoint

[1.4.0] - 2025-02-22
### Added
- **Deep Search Integration:**  
  - Introduced a multi-level deep search mode that adjusts key parameters (token count, scrape length, and search results) based on the specified depth.
- **EGOT System:**  
  - Implemented the Evolving Graph of Thought (EGOT) framework to dynamically map and visualize the agent's reasoning process using Neo4j.
- **Persistent Memory with Redis:**  
  - Added persistent session management using Redis, ensuring that session data and memory logs are maintained across interactions with the same user.

[1.5.0] - 2025-03-04
### Added
- **New RAG Tools Integration:**  
  - **Llama Index Context Window RAG:** Supports both retrieval and ingestion.
  - **HyDE RAG:** Focused on retrieval.
  - **Adaptive Retrieval-Augmented Generation RAG:** Focused on retrieval.
- **Notebooks for RAG Techniques:**  
  - Organized all the RAG techniques into dedicated notebooks, each containing detailed explanations aimed at didactic purposes.

[1.6.0] - 2025-03-09
### Added
- **Ollama Integration for Local LLM Models:**  
  - Added support for running LLM models locally through Ollama integration.
  - Users can now pull and run models directly on their machines by prefixing model names with `local_` in configuration (e.g., `local_deepseek-r1`, `local_llama3.3`, `local_phi4`).
  - Provides data privacy, cost efficiency, and offline capability for sensitive applications.
  - Automatically handles model downloading and initialization when specified models aren't already active.
  - Supports running models even without GPU by switching to CPU (with reduced performance).
- **Model-Specific Options Configuration:**  
  - Added capability to set specific options for each Ollama model.
  - Users can now customize parameters like temperature, top_p, top_k, and other inference settings on a per-model basis.
  - Supports all Ollama model configuration options including context size, repetition penalties, and sampling parameters.
  - Enables fine-tuned control over model behavior while maintaining the simplicity of the local integration.
  - Configuration options can be set through the API for advanced model tuning.

## [1.7.0] - 2025-03-23
### Added
- **OpenAI Computer Use Integration:**  
  - Integrated a new tool for browser automation, OpenAI Computer Use, which mirrors the capabilities of the OpenAI Operator. This tool is designed to execute advanced browser automation tasks with enhanced efficiency. You can find the new tool in default_tools.py under the name browser_navigation_cua.

- **WebSocket Integration:**  
  - Added a WebSocket module to provide real-time updates to the frontend. This integration continuously streams all reasoning steps and backend operations, improving transparency and user interaction.

- **OpenAI Web Search Tool Integration:**  
  - Integrated a new web search tool that utilizes the Chat Completions API. With this integration, the model retrieves information from the web before responding to queries, leveraging fine-tuned models and tools similar to those used in Search in ChatGPT. You can find the new tool in default_tools.py under the name helper_model_web_search.

## [1.8.0] - 2025-04-20
### Added
- **Dual-Mode Reinforcement Learning Agent:**
  - Implemented a versatile Q-Learning agent (`reinforcement_learning/qlearn_agent.py`) designed to learn optimal policies through experience.
  - Supports two operational modes:
    - **`simple` (Tabular Q-Learning):** Uses a traditional Q-table (dictionary) to store state-action values. Ideal for problems with small, discrete state spaces where direct value lookup is feasible.
    - **`neural` (Deep Q-Network - DQN):** Employs a neural network to approximate Q-values. This approach overcomes the "curse of dimensionality" and enables learning in environments with large or continuous state spaces by generalizing from experienced states to unseen ones.
  - Integrated with Redis and WebSockets to potentially allow for human feedback to refine the agent's policy, particularly for the DQN mode.
- **Reinforcement Learning for RAG Selection (RL Meta RAG as default tool):**
  - Introduced an RL-based system (`RlMetaRag`) that utilizes the Q-Learning agent to dynamically select the optimal RAG technique (LlamaIndex, HyDE, Adaptive RAG) based on query characteristics.
  - Uses an LLM to extract features from the user query (e.g., type, domain, complexity, ambiguity) to inform the RL agent's state specifically for RAG selection.
  - Includes a mechanism to switch between the learned RL policy and direct LLM suggestion based on the agent's recent performance (prediction error) when selecting a RAG technique.



