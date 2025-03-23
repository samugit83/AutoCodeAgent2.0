import logging
import os
import traceback
from typing import List, Dict, Optional
import requests
from openai import OpenAI
import time
from models.models_options import local_ollama_options
from params import PARAMS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
openai_logger = logging.getLogger("openai")
openai_logger.setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

class CloudClient:
    """Client for cloud calls via OpenAI's API."""
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def call(
        self,
        chat_history: List[Dict[str, any]],
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_extension: Optional[str] = None,
        model: str = "gpt-4-turbo",
        output_format: Optional[str] = None
    ) -> str:
        try:
            content_list = []

            if image_base64:
                mime_types = {
                    'png': 'image/png',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'gif': 'image/gif',
                    'webp': 'image/webp'
                }
                mime_type = mime_types.get(
                    (image_extension or '').lower(), 'image/png'
                )
                content_list.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_base64}"
                    }
                })

            if image_url:
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })

            if content_list:
                chat_history.append({
                    "role": "user",
                    "content": content_list
                })

            request_params = {
                "model": model, 
                "messages": chat_history
            }

            if output_format:
                request_params["response_format"] = {"type": output_format}

            response = self.client.chat.completions.create(**request_params)

            answer = response.choices[0].message.content.strip()
            return answer

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            logger.error(traceback.format_exc())
            raise e
        

class LocalClient:
    """
    A client for local API calls that automatically pulls a missing model if the API returns an error
    indicating that the model is not found and suggests pulling it first.
    """
    def __init__(self, base_url: str = "http://ollama:11434/api"):
        self.chat_url = f"{base_url}/chat"
        self.pull_url = f"{base_url}/pull"

    def call(self, chat_history: List[Dict[str, any]], model: str, image_base64: Optional[str] = None) -> str:
        payload = {
            "model": model,
            "messages": chat_history,
            "stream": False
        }
        if PARAMS["APPLY_MODEL_OPTIONS"]:
            payload.update(local_ollama_options)
            
        try:
            if image_base64:
                payload["images"] = [image_base64]
            response = requests.post(self.chat_url, json=payload)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                error_data = response.json()
                error_message = error_data.get("error", "")
            except Exception:
                error_message = ""

            if "try pulling it first" in error_message:
                logger.info(f"Model '{model}' not found. Pulling the model using pull API...")
                pull_payload = {"model": model}
                pull_response = requests.post(self.pull_url, json=pull_payload)
                pull_response.raise_for_status()

                pull_data = pull_response.json()
                if pull_data.get("status") == "success":
                    logger.info(f"🤖🧠 Model '{model}' pulled successfully. Retrying chat call...")
                    time.sleep(2)
                    response = requests.post(self.chat_url, json=payload)
                    response.raise_for_status()
                else:
                    error_msg = f"Failed to pull model '{model}'. Pull API response: {pull_data}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            else:
                logger.error(f"Local API error: {str(e)}")
                logger.error(traceback.format_exc())
                raise e

        data = response.json()
        logger.info(f"Local API response: {data}")
        answer = data["message"]["content"].strip()
        return answer


def call_model(
    chat_history: List[Dict[str, any]],
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_extension: Optional[str] = None,
    model: str = "gpt-4o",
    output_format: Optional[str] = None
) -> str:

    client_type = "local" if model.startswith("local_") else "cloud"

    if client_type == "cloud":
        client = CloudClient(api_key=OPENAI_API_KEY)
        return client.call(
            chat_history,
            image_url,
            image_base64,
            image_extension,
            model,
            output_format
        )
    else:
        model = model.replace("local_", "")
        client = LocalClient()
        return client.call(
            chat_history, 
            model,
            image_base64)


def create_embeddings(texts_to_embed: List[str], model: str = "text-embedding-ada-002") -> List[List[float]]:  
    client = OpenAI(api_key=OPENAI_API_KEY)  
    try:
        response = client.embeddings.create( 
            model=model,
            input=texts_to_embed 
        )
    except Exception as e:
        raise RuntimeError(f"Error while fetching embeddings from OpenAI: {e}")

    embeddings = [entry.embedding for entry in response.data]
    return embeddings
