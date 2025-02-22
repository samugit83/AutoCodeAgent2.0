import os
import shutil
import re
import logging

logger = logging.getLogger(__name__)



def move_file_to_static(file_path: str) -> str:
    """
    Moves the file from its temporary location to the static/files folder,
    and returns the URL path for the file.
    """
    destination_dir = os.path.join(os.getcwd(), 'static', 'files')
    os.makedirs(destination_dir, exist_ok=True)
    filename = os.path.basename(file_path)
    destination_path = os.path.join(destination_dir, filename)
    try:
        shutil.move(file_path, destination_path)
    except Exception as e:
        logger.error(f"Failed to move file from {file_path} to {destination_path}: {e}")
        raise
    return f"/static/files/{filename}"

def transform_final_answer(final_answer: str) -> str:
    """
    Searches for file tags with a source attribute pointing to /tmp/ and,
    if found, moves the file to the static folder and updates the snippet accordingly.
    """
    pattern = r'src=["\'](/tmp/[^"\']+)["\']'
    
    def replacement(match):
        tmp_path = match.group(1) 
        full_tmp_path = os.path.join("/tmp", os.path.basename(tmp_path))
        if os.path.exists(full_tmp_path):
            new_url = move_file_to_static(full_tmp_path)
            return f'src="{new_url}"'
        else:
            logger.error(f"File not found at {full_tmp_path}")
            return match.group(0)
    
    updated_answer = re.sub(pattern, replacement, final_answer)
    return updated_answer  


def sanitize_gpt_response(response_str: str) -> str:
    response_str = re.sub(r'^```json\s*', '', response_str, flags=re.MULTILINE)
    response_str = re.sub(r'```$', '', response_str, flags=re.MULTILINE)
    response_str = response_str.replace(": False", ": false")
    response_str = response_str.replace(": True", ": true")
    
    return response_str.strip()


