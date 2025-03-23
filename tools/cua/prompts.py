from string import Template


FIRST_URL_PROMPT = Template("""
You are a browsing assistant. Based on the user's query, please provide a valid URL that best initiates a browsing session relevant to the query.
User Query: ${user_prompt}
Instructions:
- Your response must consist solely of a single URL.
- The URL must be complete and start with "https://".
- The URL should only contain the domain without any path (e.g., "https://example.com" not "https://example.com/path").
- Do not include any additional text, explanations, or commentary.
Output:   
""")     

BROWSER_STOP_CONFIRMATION = Template("""
You are a browsing assistant. Analyze the interaction between the assistant and user to determine if the user wants to stop the browsing process or continue.

Assistant Request: ${assistant_request}
User Answer: ${user_prompt}                                

Instructions:
- Carefully analyze both the assistant's request and the user's response to understand the context.
- ONLY output "stop" if the user EXPLICITLY indicates they want to stop browsing, end the session, or move to the next step.
- Look for clear stop signals like "stop", "quit", "exit", "end", "that's enough", "I'm done", etc.
- For ANY other request, including unclear messages or additional instructions, output ONLY: continue
- Even if you don't understand the user's request, default to "continue"
- Do not include any additional text, explanations, or commentary. Output must be only "stop" or "continue"
                                     
Output:
""")