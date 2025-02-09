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
