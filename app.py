import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import pdfkit
from code_agent.code_agent import CodeAgent
from deep_search.planner import DeepSearchAgentPlanner
import logging
import traceback
import base64
from tools.rag.hybrid_vector_graph_rag.ingest_corpus import hybrid_vector_graph_rag_ingest_corpus
from tools.rag.llama_index.ingest_corpus import llama_index_ingest_corpus
from tools.rag.llama_index_context_window.ingest_corpus import llama_index_context_window_ingest_corpus
from models.models import call_model
from tools.custom_tools import CUSTOM_TOOLS
import redis
import json
from tools.rag.rl_meta_rag.rl_meta_rag_retrieve import RlMetaRag

logging.basicConfig(
    level=logging.DEBUG,  
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s'
)

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')


@app.route('/')
def index():
    return render_template('index.html')

# --- Corpus ingestion endpoints remain as HTTP ---
@app.route('/hybrid-vector-graph-rag-ingest-corpus', methods=['POST'])
def hybrid_vector_graph_rag_ingest():
    try:
        hybrid_vector_graph_rag_ingest_corpus()
        return jsonify({"message": "Script executed successfully"}), 200
    except Exception as e:
        logging.error("Exception in /hybrid-vector-graph-rag-ingest-corpus: %s", str(e))
        logging.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500               

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
        logging.error("Exception in /llama-index-ingest-corpus: %s", str(e))
        logging.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500     


@app.route('/call-test-model', methods=['GET'])
def call_test_model():
    response = call_model(
        chat_history=[{"role": "user", "content": "Tell me a story about a cat and a dog."}], 
        model="local_llama3.2:1b"
    )
    return jsonify({"response": response}), 200


# --- Main agent run via Socket.IO ---
@socketio.on('run_agent')
def handle_run_agent(data):
    session_id = data.get('session_id')

    def background_task(data, session_id):
        try:
            deep_search_enabled = data.get('deepsearch', False)
            
            if deep_search_enabled:
                required_fields = ['session_chat_history']
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    socketio.emit('error', {"session_id": session_id, "error": f"Missing required fields: {', '.join(missing_fields)}"})
                    return

                user_id = data.get('user_id')
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
                    encoded_pdf = base64.b64encode(pdf).decode('utf-8')
                    socketio.emit('agent_response', {
                        "session_id": session_id,   
                        "assistant": encoded_pdf, 
                        "content_type": "application/pdf"
                    })
                else:
                    socketio.emit('agent_response', {"session_id": session_id, "assistant": answer})
            else:
                chat_history = data.get('session_chat_history', [])
                code_agent = CodeAgent(
                    chat_history=chat_history,
                    tools=CUSTOM_TOOLS,
                    use_default_tools=True,
                    session_id=session_id,
                    socketio=socketio
                )
                final_answer = code_agent.run_agent()
                socketio.emit('agent_response', {"session_id": session_id, "assistant": final_answer})

        except Exception as e:
            logging.error("Exception in background_task: %s", str(e))
            logging.error(traceback.format_exc())
            socketio.emit('error', {"session_id": session_id, "error": str(e)})

    # Launch your task as a background thread:
    socketio.start_background_task(background_task, data, session_id)


@socketio.on('follow_up_response')
def handle_follow_up_response(data):
    redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)
    session_id = data.get("session_id")
    message = data.get("message")
    if session_id and message:
        redis_key = f"followup:{session_id}"
        redis_client.set(redis_key, message)


@socketio.on('submit_evaluation')
def handle_submit_evaluation(data):
    """
    Receives evaluation feedback from the frontend (a rating between 1 and 5),
    retrieves stored RL update data from Redis, updates the Q-learning agent, and
    deletes the stored data.
    """
    meta_rag = RlMetaRag()
    session_id = data.get('session_id')
    rating = data.get('rating')  # Expected to be a number between 1 and 5

    if not session_id or rating is None:
        emit('evaluation_ack', {'status': 'error', 'message': 'session_id and rating are required.'})
        return

    redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)
    redis_key = f"rl_update:{session_id}"
    stored_data = redis_client.get(redis_key)

    if stored_data:
        try:
            data_dict = json.loads(stored_data)
            state = data_dict.get('state')
            action = data_dict.get('action')

            # Convert state and action to tuples if they are lists, ensuring they are hashable.
            if isinstance(state, list):
                state = tuple(state)
            if isinstance(action, list):
                action = tuple(action)

            reward = float(rating)
            meta_rag.agent.update_q_value(state, action, reward, use_next_state=False)
            redis_client.delete(redis_key)
        except Exception as e:
            logging.error("Error processing evaluation: %s", str(e))
    else:
        logging.error("No stored evaluation data found for this session.")



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.getenv('FLASK_PORT', 5000)), debug=True)

