from flask import Flask, request, jsonify, render_template, send_file
import os
import io
import pdfkit
from code_agent.code_agent import CodeAgent
from deep_search.planner import DeepSearchAgentPlanner
import logging
import traceback
from tools.rag.hybrid_vector_graph_rag.ingest_corpus import hybrid_vector_graph_rag_ingest_corpus
from tools.rag.llama_index.ingest_corpus import llama_index_ingest_corpus
from tools.rag.llama_index_context_window.ingest_corpus import llama_index_context_window_ingest_corpus
from models.models import call_model

logging.basicConfig(
    level=logging.DEBUG,  
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s'
)

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run-agent', methods=['POST'])
def run_agent():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        deep_search_enabled = data.get('deepsearch', False)

        if deep_search_enabled:
            required_fields = ['session_chat_history']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400

            session_id = data.get('session_id', None)
            user_id = data.get('user_id', None)
            chat_history = data['session_chat_history']
            depth = data.get('depth', 1)
            data_sources = ['websearch']
            planner = DeepSearchAgentPlanner(
                chat_history,
                is_interactive=True,
                session_id=session_id,
                user_id=user_id,
                depth=depth,
                data_sources=data_sources,
                delete_graph=True
            )
            planner.run_planner()
            answer = planner.data.final_answer

            if '<html><body>' in answer:
                pdf = pdfkit.from_string(answer, False)
                return send_file(
                    io.BytesIO(pdf),
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name='deep_search_output.pdf'
                )
            else:
                return jsonify({"assistant": answer}), 200
        else: 
            chat_history = data.get('session_chat_history', [])

            tools = [ 
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

            code_agent = CodeAgent(
                chat_history=chat_history,
                tools=tools,
                use_default_tools=True
            )

            final_answer = code_agent.run_agent()
            return jsonify({"assistant": final_answer}), 200

    except Exception as e:
        logging.error("Exception occurred in /run-agent: %s", str(e))
        logging.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


#start the acquisition, parsing, and ingestion of all documents present in /tools/rag/hybrid_vector_graph_rag/corpus
@app.route('/hybrid-vector-graph-rag-ingest-corpus', methods=['POST'])
def hybrid_vector_graph_rag_ingest():
    try:
        hybrid_vector_graph_rag_ingest_corpus()
        return jsonify({"message": "Script executed successfully"}), 200
    except Exception as e:
        logging.error("Exception occurred in /hybrid-vector-graph-rag-ingest-corpus: %s", str(e))  
        logging.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500               
     

#start the acquisition, parsing, and ingestion of all documents present in /tools/rag/llama_index/corpus
# or /tools/rag/llama_index_context_window/corpus if isContextWindow is true
@app.route('/llama-index-ingest-corpus', methods=['POST'])
def llama_index_ingest():
    try:
        data = request.get_json()
        is_context_window = data.get('isContextWindow', False)
        
        if is_context_window:
            llama_index_context_window_ingest_corpus()
        else:
            llama_index_ingest_corpus()
        
        return jsonify({"message": "Script executed successfully"}), 200
    except Exception as e:
        logging.error("Exception occurred in /llama-index-ingest-corpus: %s", str(e))  
        logging.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500     



@app.route('/call-test-model', methods=['GET'])
def call_test_model():
    response = call_model(
        chat_history=[{"role": "user", "content": "Tell me a story about a cat and a dog."}], 
        model="local_llama3.2:1b"
    )
    return jsonify({"response": response}), 200


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=True
    ) 

