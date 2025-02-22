import os
import requests
import json
from requests.exceptions import RequestException
from bs4 import BeautifulSoup

def truncate_content(text: str, max_length: int) -> str:
    """Truncate text to a maximum length."""
    return text if len(text) <= max_length else text[:max_length]

class GoogleSearchTool:
    """
    Performs a Google web search using either SerpAPI or Serper.
    Returns structured JSON for each result.
    
    Ensure you set the corresponding environment variable for the API key:
      - SERPAPI_API_KEY for SerpAPI
      - SERPER_API_KEY for Serper
    """
    def __init__(self, provider: str = "serpapi"):
        self.provider = provider
        if provider == "serpapi":
            self.organic_key = "organic_results"
            self.api_key = os.getenv("SERPAPI_API_KEY")
        else:
            self.organic_key = "organic"
            self.api_key = os.getenv("SERPER_API_KEY")
        if self.api_key is None:
            raise ValueError("Missing API key. Please set the 'GoogleSearchTool' api key environment variable.")

    def search(self, query: str, filter_year: int = None, max_search_results: int = None) -> dict:
        if self.provider == "serpapi":
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "google_domain": "google.com",
            }
            base_url = "https://serpapi.com/search.json"
        else:
            params = {
                "q": query,
                "api_key": self.api_key,
            }
            base_url = "https://google.serper.dev/search"
        
        if filter_year is not None:
            params["tbs"] = f"cdr:1,cd_min:01/01/{filter_year},cd_max:12/31/{filter_year}"

        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            results = response.json()
        else:
            raise ValueError(response.json())

        if self.organic_key not in results:
            if filter_year is not None:
                raise Exception(
                    f"No results found for query: '{query}' with filtering on year={filter_year}. "
                    "Use a less restrictive query or remove the year filter."
                )
            else:
                raise Exception(f"No results found for query: '{query}'. Use a less restrictive query.")

        organic_results = results[self.organic_key]
        if not organic_results:
            year_filter_message = f" with filter year={filter_year}" if filter_year is not None else ""
            raise Exception(f"No results found for '{query}'{year_filter_message}.")

        structured_results = []
        for idx, page in enumerate(organic_results):
            result_entry = {
                "index": idx,
                "title": page.get("title", ""),
                "link": page.get("link", ""),
                "date": page.get("date", ""),
                "source": page.get("source", ""),
                "snippet": page.get("snippet", ""),
            }
            structured_results.append(result_entry)

        if max_search_results is not None:
            structured_results = structured_results[:max_search_results]

        return {"query": query, "filter_year": filter_year, "results": structured_results}

class VisitWebpageTool:
    """
    Visits a webpage and returns its visible text content without any markup.
    If max_length is provided, the content is truncated.
    """
    def __init__(self, max_length: int = None):
        self.max_length = max_length

    def visit(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            text_content = soup.get_text(separator='\n', strip=True)
            if self.max_length is not None:
                return truncate_content(text_content, self.max_length)
            return text_content
        except requests.exceptions.Timeout:
            return "The request timed out. Please try again later or check the URL."
        except RequestException as e:
            return f"Error fetching the webpage: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

def search_and_scrape(query: str,
                      filter_year: int = None,
                      provider: str = "serpapi",
                      max_search_results: int = None,
                      max_length: int = None,
                      logger = None,
                      enrich_log = None) -> dict:
    """
    Uses GoogleSearchTool to perform a search and then uses VisitWebpageTool
    to scrape the content of each result. Returns a JSON structure with search info and scraped content.
    """
    search_tool = GoogleSearchTool(provider=provider)
    visit_tool = VisitWebpageTool(max_length=max_length)

    search_results = search_tool.search(query, filter_year, max_search_results)
    if logger:
        logger.info(enrich_log(f"🌐 GoogleSearchTool results: {json.dumps(search_results, indent=4)}", "add_green_divider"), extra={"no_memory": True})
    results_with_content = []

    for result in search_results["results"]:
        url = result["link"]
        if url:
            content = visit_tool.visit(url)
        else:
            content = "No URL provided."
        result_with_content = result.copy()
        result_with_content["content"] = content
        results_with_content.append(result_with_content)

    return {
        "query": query,
        "results": results_with_content
    }

class WebSearchAgent:
    """
    A single agent class that initializes the search tools and calls the search_and_scrape method.
    """
    def __init__(self, provider: str = "serpapi", max_search_results: int = 3, max_length: int = None, logger = None, enrich_log = None):
        self.provider = provider
        self.max_search_results = max_search_results
        self.max_length = max_length
        self.logger = logger
        self.enrich_log = enrich_log
        
    def run_search(self, query: str, filter_year: int = None) -> dict:
        """
        Executes a web search and scraping operation using the provided query.
        
        Parameters:
          - query: The search query.
          - filter_year: Optional year filter.
        
        Returns:
          - A dictionary containing the query and a list of search results with scraped content.
        """
        results = search_and_scrape(
            query=query,
            filter_year=filter_year,
            provider=self.provider,
            max_search_results=self.max_search_results,
            max_length=self.max_length,
            logger=self.logger,
            enrich_log=self.enrich_log
        )
        return results