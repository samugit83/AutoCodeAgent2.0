
from flask import Flask, request, jsonify, render_template
import os
from code_agent.code_agent import CodeAgent
import logging
import traceback
from tools.rag.hybrid_vector_graph_rag.ingest_corpus import ingest_corpus

logging.basicConfig(
    level=logging.DEBUG,  
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s'
)

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

    
@app.route('/run-code-agent', methods=['POST'])
def run_code_agent():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is empty"}), 400

        chat_history = data.get('session_chat_history', [])

        tools = [ 
            {
                "tool_name": "numpy",
                "lib_names": ["numpy"]
            },
            {    
                "tool_name": "geopy",
                "lib_names": ["geopy"], 
                "instructions": "A library to get the coordinates of a given location.",
                "code_example": """
                    
                    def get_coordinates(previous_output):
                    
                        from geopy.geocoders import Nominatim
                        updated_dict = previous_output.copy()

                        user_agent = "my-app/1.0"
                        location = updated_dict.get("location", "")
                    
                        geolocator = Nominatim(user_agent=user_agent)

                        try: 
                            # Geocode the location
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
            }
        ]

 
        code_agent = CodeAgent(
            chat_history=chat_history,
            tools=tools,
        )

        final_answer = code_agent.run_agent()
        return jsonify({"assistant": final_answer}), 200
    
    except Exception as e:
        logging.error("Exception occurred in /run-code-agent: %s", str(e))
        logging.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/hybrid-vector-graph-rag-ingest-corpus', methods=['POST'])
def hybrid_vector_graph_rag_ingest_corpus():
    try:
        ingest_corpus()
        return jsonify({"message": "Script executed successfully"}), 200
    except Exception as e:
        logging.error("Exception occurred in /hybrid-vector-graph-rag-ingest-corpus: %s", str(e))  
        logging.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500               
     
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=True
    )
