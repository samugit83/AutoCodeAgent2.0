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

