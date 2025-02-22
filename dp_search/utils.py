import re

def sanitize_gpt_response(response_str: str) -> str:
    response_str = re.sub(r'^```json\s*', '', response_str, flags=re.MULTILINE)
    response_str = re.sub(r'```$', '', response_str, flags=re.MULTILINE)
    response_str = response_str.replace(": False", ": false")
    response_str = response_str.replace(": True", ": true")
    
    return response_str.strip()


def remove_html_body_tags(html_str: str) -> str:
    cleaned_str = re.sub(r'</?(html|body)[^>]*>', '', html_str, flags=re.IGNORECASE)
    return cleaned_str.strip()


def apply_depth_settings(planner, depth):
    """
    Update planner instance attributes based on the provided depth.
    
    Args:
        planner: An instance of DeepSearchAgentPlanner.
        depth (int): The current depth to use for configuration.
    """
    
    if depth == 1:
        planner.min_token_output_type_final = 3000
        planner.min_output_type_final = 1
        planner.min_output_type_functional = 1
        planner.max_scrape_length = 60000
        planner.max_search_results = 1
    elif depth == 2:
        planner.min_token_output_type_final = 5000
        planner.min_output_type_final = 2
        planner.min_output_type_functional = 2
        planner.max_scrape_length = 80000
        planner.max_search_results = 2
    elif depth >= 3:
        planner.min_token_output_type_final = 7000
        planner.min_output_type_final = 3
        planner.min_output_type_functional = 3
        planner.max_scrape_length = 100000
        planner.max_search_results = 3
    elif depth >= 4:
        planner.min_token_output_type_final = 9000
        planner.min_output_type_final = 4
        planner.min_output_type_functional = 4
        planner.max_scrape_length = 120000
        planner.max_search_results = 4
    else:
        planner.min_token_output_type_final = 11000
        planner.min_output_type_final = 5
        planner.min_output_type_functional = 5
        planner.max_scrape_length = 140000
        planner.max_search_results = 5