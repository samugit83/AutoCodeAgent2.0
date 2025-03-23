CUSTOM_TOOLS = [ 
                {
                    "tool_name": "numpy",
                    "lib_names": ["numpy"],
                    "type": "standard_custom"
                },
                {    
                    "tool_name": "geopy",
                    "lib_names": ["geopy"], 
                    "type": "standard_custom",
                    "instructions": "A library to get the coordinates of a given location.",
                    "code_example": """
def get_coordinates(previous_output):
    from geopy.geocoders import Nominatim
    updated_dict = previous_output.copy()
    user_agent = "my-app/1.0"
    location = updated_dict.get("location", "")
    geolocator = Nominatim(user_agent=user_agent)
    try: 
        geo_location = geolocator.geocode(location)
        if geo_location:
            updated_dict["coordinates"] = (geo_location.latitude, geo_location.longitude)
        else:
            updated_dict["coordinates"] = None
        return updated_dict
    except Exception as error:
        logger.error(f"Error retrieving coordinates: {error}")
        return previous_output
                    """ 
                },   
                {   
                    "langchain_tool_name": "serpapi", 
                    "type": "langchain_tool" 
                },
                {
                    "langchain_tool_name": "eleven_labs_text2speech",
                    "type": "langchain_tool",
                },
                {
                    "langchain_tool_name": "openweathermap-api",  
                    "type": "langchain_tool"
                }
            ]  
