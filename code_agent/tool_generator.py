import copy
import os
import logging
from string import Template
from langchain_community.agent_toolkits.load_tools import load_tools
from .default_tools import DEFAULT_TOOLS, TOOLS_ACTIVATION
from params import PARAMS


logger = logging.getLogger(__name__)

def substitute_variables_in_value(value, variables):
    """Helper: substitutes variables in a string or list of strings."""
    if isinstance(value, str):
        tmpl = Template(value)
        try:
            return tmpl.substitute(variables)
        except KeyError as e:
            logger.error(f"Missing substitution for variable {e} in string value.")
            return tmpl.safe_substitute(variables)
    elif isinstance(value, list):
        new_list = [] 
        for item in value:
            if isinstance(item, str):
                tmpl = Template(item)
                try:
                    new_list.append(tmpl.substitute(variables))
                except KeyError as e:
                    logger.error(f"Missing substitution for variable {e} in list item.")
                    new_list.append(tmpl.safe_substitute(variables))
            else:
                new_list.append(item)
        return new_list
    return value
 


def generate_tools(user_tools, use_default_tools):
    """
    Processes the list of tool dictionaries:
      - For non-LangChain tools, applies dynamic variable substitution using Python's string.Template.
      - For tools where "tool_name" is "load_langchain_tool", loads the LangChain tool using its
        additional parameters and converts it into the default schema using LangChainToolConverter.
    
    Args:
        tools (list): The list of tool dictionaries.
    Returns:
        list: A new list of tools with variables applied or converted from LangChain tools.
    """
    tools = user_tools + DEFAULT_TOOLS if use_default_tools else user_tools
    updated_tools = [] 
      
    # Define variables to substitute.
    variables = {
        "TOOL_HELPER_MODEL": PARAMS["TOOL_HELPER_MODEL"],
        "TOOL_HELPER_MODEL_WEB_SEARCH": PARAMS["TOOL_HELPER_MODEL_WEB_SEARCH"],
        "JSON_PLAN_MODEL": PARAMS["JSON_PLAN_MODEL"],
        "EVALUATION_MODEL": PARAMS["EVALUATION_MODEL"],
        "GMAILUSER": os.getenv("GMAILUSER", ""),
        "PASSGMAILAPP": os.getenv("PASSGMAILAPP", "")
    }
    
    for tool in tools:
        if tool.get("type") == "langchain_tool":
            langchain_tool_name = tool.get("langchain_tool_name")
            additional_parameters = tool.get("additional_parameters", {})
            try:
                loaded_tools = load_tools([langchain_tool_name], **additional_parameters)
                if loaded_tools:
                    langchain_tool_instance = loaded_tools[0]
                    converted_tool = LangChainToolConverter.from_langchain_tool(langchain_tool_name, langchain_tool_instance, additional_parameters)
                    updated_tools.append(converted_tool)
                else:
                    logger.error(f"No LangChain tool was loaded for '{langchain_tool_name}'.")
            except Exception as e:
                logger.error(f"Error loading LangChain tool '{langchain_tool_name}': {e}", exc_info=True)
        
        elif tool.get("type") == "standard_custom":
            tool_copy = copy.deepcopy(tool)
            tool_copy.pop("type", None)  
            for key, value in tool_copy.items():
                tool_copy[key] = substitute_variables_in_value(value, variables)
            updated_tools.append(tool_copy)
        else:
            if not TOOLS_ACTIVATION.get(tool.get("tool_name"), False):
                logger.info(f"Skipping tool {tool.get('tool_name')} due to activation flag being False.")
                continue
            tool_copy = copy.deepcopy(tool)
            for key, value in tool_copy.items():
                tool_copy[key] = substitute_variables_in_value(value, variables)
            updated_tools.append(tool_copy)

    logger.info(f"Updated tools: {updated_tools}")

    return updated_tools


class LangChainToolConverter: 
    """
    Converts a LangChain tool instance into our default tool schema. 
    The schema contains:
      - tool_name: The lowercased name of the tool.
      - lib_names: A list of library names (inferred from the tool's module).
      - instructions: The tool's description.
      - inputs: A dict of expected inputs (if provided by the tool).
      - output_type: The tool's output type (defaulting to "string" if not present).
      - use_exactly_code_example: A flag indicating that the code example should be used verbatim.
      - code_example: A standardized code snippet showing how to call the tool.
    """

    @staticmethod
    def from_langchain_tool(langchain_tool_name, langchain_tool, additional_parameters) -> dict:
        tool_name = getattr(langchain_tool, "name", "unknown_tool").lower()
        instructions = getattr(langchain_tool, "description", "No instructions provided")

        inputs = {}
        if hasattr(langchain_tool, "args") and isinstance(langchain_tool.args, dict):
            inputs = {
                key: {**value, "description": value.get("description", "No description provided")}
                for key, value in langchain_tool.args.items()
            }
            for input_detail in inputs.values():
                input_detail.pop("title", None)

        output_type = getattr(langchain_tool, "output_type", "string")
        tool_name = "langchain_tool_" + tool_name
        code_example = LangChainToolConverter.generate_code_example(langchain_tool_name, inputs, output_type, tool_name, additional_parameters)

        return {
            "tool_name": tool_name,
            "lib_names": ["langchain_community.agent_toolkits.load_tools"],
            "instructions": instructions,
            "use_exactly_code_example": True,
            "code_example": code_example
        }

    @staticmethod
    def generate_code_example(langchain_tool_name: str, inputs: dict, output_type: str, tool_name: str, additional_parameters: dict) -> str:
        additional_params_kwargs = ", ".join(
            f'{key}="{value}"' if isinstance(value, str) else f"{key}={value}"
            for key, value in additional_parameters.items()
        )
        expected_inputs_comment = "\n".join(
            [f"    #   {key}: {val.get('description', 'No description provided')}" for key, val in inputs.items()]
        )
        code_example = f'''
def {tool_name}(previous_output) -> dict:
    from langchain_community.agent_toolkits.load_tools import load_tools
    try:
        updated_dict = previous_output.copy()
        # Expected inputs:
{expected_inputs_comment}
        # Dynamically build the tool input based on expected inputs and the updated_dict
        tool_input = "<construct the tool input from updated_dict based on the expected inputs>"
        # Load the tool with the provided additional parameters as kwargs
        tool = load_tools(['{langchain_tool_name}'], {additional_params_kwargs})[0]
        # output type is {output_type}
        output = tool.run(tool_input)
        updated_dict["{tool_name}_output"] = output
        return updated_dict
    except Exception as error:
        logger.error(f"Error sending email: {{error}}")
        return previous_output
'''
        return code_example