import logging  
import os
import traceback 
from typing import List, Dict, Optional
from openai import OpenAI

 
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



def call_model(
    chat_history: List[Dict[str, any]],
    text_prompt: Optional[str] = None,
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_extension: Optional[str] = None,
    model: str = "gpt-4o",
    output_format: Optional[str] = None
) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        content_list = []

        if text_prompt:
            content_list.append({
                "type": "text",
                "text": text_prompt
            })

        if image_base64:

            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'webp': 'image/webp'
            }
            
            # Default to png if extension not recognized
            mime_type = mime_types.get(image_extension.lower() if image_extension else '', 'image/png')
            
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

        if output_format:
            response = client.chat.completions.create( 
                model=model,
                messages=chat_history, 
                temperature=0.0,
                response_format={"type": output_format}
            )
        else:
            response = client.chat.completions.create( 
                model=model,
                messages=chat_history, 
                temperature=0.0
            )

        answer = response.choices[0].message.content.strip() 
        return answer

    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        logger.error(traceback.format_exc())
        raise e
     

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
