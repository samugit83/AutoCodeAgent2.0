import re

class JsonResponseHandler:
    @staticmethod
    def sanitize_response(response_str: str) -> str:
        response_str = re.sub(r'^```json\s*', '', response_str, flags=re.MULTILINE)
        response_str = re.sub(r'```$', '', response_str, flags=re.MULTILINE)
        
        response_str = re.sub(
            r'"\s*"\s*', 
            '', 
            response_str,
            flags=re.MULTILINE 
        )
        
        return response_str.strip()
    

    @staticmethod
    def update_task_structure(original_json, new_json):
        existing_tasks = original_json.get('tasks', [])
        if 'updated_result_validation_tasks' in new_json:
            task_name_to_index = {task['task_name']: index for index, task in enumerate(existing_tasks)}
            
            for updated_task in new_json['updated_result_validation_tasks']:   
                task_name = updated_task['task_name']
                if task_name in task_name_to_index: 
                    existing_tasks[task_name_to_index[task_name]]['result_validation'] = updated_task['result_validation']

        if 'new_task' in new_json:
            existing_tasks.append(new_json['new_task']) 

        original_json['tasks'] = existing_tasks
        for key in new_json:
            if key not in ['new_task', 'updated_result_validation_tasks']:
                original_json[key] = new_json[key]
        return original_json
