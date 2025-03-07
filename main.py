from flask import Flask, request, jsonify, render_template
import openai
import os
from dotenv import load_dotenv
from models import db, ChatThread

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Configure SQLAlchemy (using SQLite here)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///threads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

# OpenAI Client
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Assistant IDs
follow_up_question_asistant_id = "asst_wfRqJazEkW7eUH5LzDQQXih3"
behavior_assistant_id = "asst_elUaQ75paOpcDi5lkPjls5xQ"
rmw_assistant_id = "asst_6mpToleitowu2HHKGze0P0GX"
aux_assistant_id = "asst_KzQQpjyPdM71MyygP7SxEyRM"
blindspot_assistant_id = "asst_HowmEO015nb7cOwc2K1TnhlH"
Emotion_and_feeling_assistant_id = "asst_vXcEIHkBuhhRZL7w0PFfjMb6"
Higher_Intelligence_Pursuit_assistant_id = "asst_SoMKjSJIYJQGlAWqa7PNH4O4"
self_actualization_assistant_id = "asst_wY8Qf822dtUlBsGAM5vwJtyT"
stad_assistant_id = "asst_KpXdl3ETnxVT6NasbqZ3pJr4"


MAX_QUESTIONS = 20  # Limit on follow-up questions

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message")
    if not user_message:
        return jsonify({"response": "Please enter a message."})

    # Retrieve or create a thread record from the database
    thread = ChatThread.query.first()
    if thread is None:
        new_thread = openai_client.beta.threads.create()
        thread = ChatThread(thread_id=new_thread.id)
        db.session.add(thread)
        db.session.commit()

    # Add user message to the thread
    try:
        openai_client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user",
            content=user_message
        )
    except openai.NotFoundError:
        # Create new thread if the previous one is lost
        new_thread = openai_client.beta.threads.create()
        thread.thread_id = new_thread.id
        db.session.commit()
        openai_client.beta.threads.messages.create(
            thread_id=thread.thread_id,
            role="user",
            content=user_message
        )

    # Fetch all messages
    messages = openai_client.beta.threads.messages.list(thread_id=thread.thread_id)
    previous_assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]

    if len(previous_assistant_messages) >= MAX_QUESTIONS:
        return jsonify({"response": "You've provided great insights. Please start a new chat if needed."})

    # Generate a follow-up question
    instructions = (
        """
        You are a mental health coach. Generate a follow-up question based on the user's response. 
        The question should be short and focus on understanding how the user feels or thinks or behaves.
        Do not ask the user questions like "What do you think will fix this"
        """
    )

    run = openai_client.beta.threads.runs.create_and_poll(
        thread_id=thread.thread_id,
        assistant_id=follow_up_question_asistant_id,
        instructions=instructions
    )

    if run.status == 'completed':
        messages = openai_client.beta.threads.messages.list(thread_id=thread.thread_id)
        last_message = messages.data[0]
        candidate = last_message.content[0].text.value
        return jsonify({"response": candidate})
    else:
        return jsonify({"response": "There was an error generating the follow-up question."})
    
def process_behavior_assistant(formatted_chat):
    """Processes chat history using the Behavior Identification Assistant."""
    try:
        temp_behavior_thread = openai_client.beta.threads.create()
        behavior_thread_id = temp_behavior_thread.id  

        openai_client.beta.threads.messages.create(
            thread_id=behavior_thread_id,
            role="user",
            content=f"Here is the conversation history:\n{formatted_chat}"
        )

        behavior_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=behavior_thread_id,
            assistant_id=behavior_assistant_id,
            instructions="Analyze the user's behavior based on the provided conversation history and provide insights."
        )

        if behavior_analysis_run.status == 'completed':
            behavior_messages = openai_client.beta.threads.messages.list(thread_id=behavior_thread_id)
            behavior_response = behavior_messages.data[0].content[0].text.value
        else:
            behavior_response = "Error generating behavior analysis report."

        openai_client.beta.threads.delete(thread_id=behavior_thread_id)
        return behavior_response

    except Exception as e:
        return f"Error in Behavior Assistant: {str(e)}"


def process_rmw_assistant(follow_up_text, behavior_response):
    """Processes behavior analysis using the RMW Assistant."""
    try:
        temp_rmw_thread = openai_client.beta.threads.create()
        rmw_thread_id = temp_rmw_thread.id  

        openai_client.beta.threads.messages.create(
            thread_id=rmw_thread_id,
            role="user",
            content=f"Follow-up questions:\n{follow_up_text}\n\nBehavior Analysis:\n{behavior_response}"
        )

        rmw_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=rmw_thread_id,
            assistant_id=rmw_assistant_id,
            instructions=""
        )

        if rmw_analysis_run.status == 'completed':
            rmw_messages = openai_client.beta.threads.messages.list(thread_id=rmw_thread_id)
            rmw_response = rmw_messages.data[0].content[0].text.value
        else:
            rmw_response = "Error generating RMW analysis report."

        openai_client.beta.threads.delete(thread_id=rmw_thread_id)
        return rmw_response

    except Exception as e:
        return f"Error in RMW Assistant: {str(e)}"


def process_aux_assistant(formatted_chat, behavior_response):
    """Processes behavior analysis using the Auxiliary Faculty Assistant."""
    try:
        temp_aux_thread = openai_client.beta.threads.create()
        aux_thread_id = temp_aux_thread.id  

        openai_client.beta.threads.messages.create(
            thread_id=aux_thread_id,
            role="user",
            content=f"Chat History:\n{formatted_chat}\n\nBehavior Patterns:\n{behavior_response}"
        )

        aux_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=aux_thread_id,
            assistant_id=aux_assistant_id,
            instructions=""
        )

        if aux_analysis_run.status == 'completed':
            aux_messages = openai_client.beta.threads.messages.list(thread_id=aux_thread_id)
            aux_response = aux_messages.data[0].content[0].text.value
        else:
            aux_response = "Error generating Auxiliary Faculty analysis report."

        openai_client.beta.threads.delete(thread_id=aux_thread_id)
        return aux_response

    except Exception as e:
        return f"Error in Auxiliary Faculty Assistant: {str(e)}"


def process_blindspot_assistant(rmw_response, behavior_response, formatted_chat):
    """Processes behavior analysis using the Blindspot Assistant."""
    try:
        temp_blindspot_thread = openai_client.beta.threads.create()
        blindspot_thread_id = temp_blindspot_thread.id  

        openai_client.beta.threads.messages.create(
            thread_id=blindspot_thread_id,
            role="user",
            content=f"RMW Score:\n{rmw_response}\n\nBehavior Patterns:\n{behavior_response}\n\nChat History:\n{formatted_chat}"
        )

        blindspot_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=blindspot_thread_id,
            assistant_id=blindspot_assistant_id,
            instructions=""
        )

        if blindspot_analysis_run.status == 'completed':
            blindspot_messages = openai_client.beta.threads.messages.list(thread_id=blindspot_thread_id)
            blindspot_response = blindspot_messages.data[0].content[0].text.value
        else:
            blindspot_response = "Error generating Blindspot analysis report."

        openai_client.beta.threads.delete(thread_id=blindspot_thread_id)
        return blindspot_response

    except Exception as e:
        return f"Error in Blindspot Assistant: {str(e)}"


def process_emotion_assistant(rmw_response, behavior_response, formatted_chat):
    """Processes behavior analysis using the Emotion and Feeling Assistant."""
    try:
        temp_emotion_thread = openai_client.beta.threads.create()
        emotion_thread_id = temp_emotion_thread.id  

        openai_client.beta.threads.messages.create(
            thread_id=emotion_thread_id,
            role="user",
            content=f"RMW Score:\n{rmw_response}\n\nBehavior Patterns:\n{behavior_response}\n\nChat History:\n{formatted_chat}"
        )

        emotion_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=emotion_thread_id,
            assistant_id=Emotion_and_feeling_assistant_id,
            instructions=""
        )

        if emotion_analysis_run.status == 'completed':
            emotion_messages = openai_client.beta.threads.messages.list(thread_id=emotion_thread_id)
            emotion_response = emotion_messages.data[0].content[0].text.value
        else:
            emotion_response = "Error generating Emotion and Feeling analysis report."

        openai_client.beta.threads.delete(thread_id=emotion_thread_id)
        return emotion_response

    except Exception as e:
        return f"Error in Emotion and Feeling Assistant: {str(e)}"

def process_higher_intelligence_pursuit_assistant(rmw_response, behavior_response, formatted_chat):
    """Processes analysis using the Higher Intelligence Pursuit Assistant."""
    try:
        temp_intelligence_thread = openai_client.beta.threads.create()
        intelligence_thread_id = temp_intelligence_thread.id  

        openai_client.beta.threads.messages.create(
            thread_id=intelligence_thread_id,
            role="user",
            content=f"RMW Score:\n{rmw_response}\n\nBehavior Patterns:\n{behavior_response}\n\nChat History:\n{formatted_chat}"
        )

        intelligence_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=intelligence_thread_id,
            assistant_id=Higher_Intelligence_Pursuit_assistant_id,
            instructions=""
        )

        if intelligence_analysis_run.status == 'completed':
            intelligence_messages = openai_client.beta.threads.messages.list(thread_id=intelligence_thread_id)
            intelligence_response = intelligence_messages.data[0].content[0].text.value
        else:
            intelligence_response = "Error generating Higher Intelligence Pursuit analysis report."

        openai_client.beta.threads.delete(thread_id=intelligence_thread_id)
        return intelligence_response

    except Exception as e:
        return f"Error in Higher Intelligence Pursuit Assistant: {str(e)}"


def process_self_actualization_assistant(rmw_response, behavior_response, formatted_chat):
    """Processes analysis using the Self-Actualization Assistant."""
    try:
        temp_self_actualization_thread = openai_client.beta.threads.create()
        self_actualization_thread_id = temp_self_actualization_thread.id  

        openai_client.beta.threads.messages.create(
            thread_id=self_actualization_thread_id,
            role="user",
            content=f"RMW Score:\n{rmw_response}\n\nBehavior Patterns:\n{behavior_response}\n\nChat History:\n{formatted_chat}"
        )

        self_actualization_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=self_actualization_thread_id,
            assistant_id=self_actualization_assistant_id,
            instructions=""
        )

        if self_actualization_analysis_run.status == 'completed':
            self_actualization_messages = openai_client.beta.threads.messages.list(thread_id=self_actualization_thread_id)
            self_actualization_response = self_actualization_messages.data[0].content[0].text.value
        else:
            self_actualization_response = "Error generating Self-Actualization analysis report."

        openai_client.beta.threads.delete(thread_id=self_actualization_thread_id)
        return self_actualization_response

    except Exception as e:
        return f"Error in Self-Actualization Assistant: {str(e)}"


def process_stad_assistant(rmw_response, behavior_response, formatted_chat):
    """Processes analysis using the STAD Assistant."""
    try:
        temp_stad_thread = openai_client.beta.threads.create()
        stad_thread_id = temp_stad_thread.id  

        openai_client.beta.threads.messages.create(
            thread_id=stad_thread_id,
            role="user",
            content=f"RMW Score:\n{rmw_response}\n\nBehavior Patterns:\n{behavior_response}\n\nChat History:\n{formatted_chat}"
        )

        stad_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=stad_thread_id,
            assistant_id=stad_assistant_id,
            instructions=""
        )

        if stad_analysis_run.status == 'completed':
            stad_messages = openai_client.beta.threads.messages.list(thread_id=stad_thread_id)
            stad_response = stad_messages.data[0].content[0].text.value
        else:
            stad_response = "Error generating STAD analysis report."

        openai_client.beta.threads.delete(thread_id=stad_thread_id)
        return stad_response

    except Exception as e:
        return f"Error in STAD Assistant: {str(e)}"


@app.route("/generate_report", methods=["POST"])
def generate_report():
    try:
        thread = ChatThread.query.first()
        if not thread:
            return jsonify({"summary": "No chat history available."})

        # Retrieve chat history
        messages = openai_client.beta.threads.messages.list(thread_id=thread.thread_id)
        chat_history = [
            f"{msg.role.capitalize()}: {msg.content[0].text.value}" for msg in reversed(messages.data)
        ]

        formatted_chat = "\n".join(chat_history)

        ### ✅ Step 1: Get Behavior Analysis ###
        behavior_response = process_behavior_assistant(formatted_chat)

        ### ✅ Step 2: Extract Follow-Up Questions ###
        follow_up_questions = [
            msg.content[0].text.value for msg in messages.data if msg.role == "assistant"
        ]
        follow_up_text = "\n".join(follow_up_questions)

        ### ✅ Step 3: Get RMW Analysis ###
        rmw_response = process_rmw_assistant(follow_up_text, behavior_response)

        ### ✅ Step 4: Get Auxiliary Faculty Analysis ###
        aux_response = process_aux_assistant(formatted_chat, behavior_response)

        ### ✅ Step 5: Get Blindspot Analysis ###
        blindspot_response = process_blindspot_assistant(rmw_response, behavior_response, formatted_chat)

        ### ✅ Step 6: Get Emotion and Feeling Analysis ###
        emotion_response = process_emotion_assistant(rmw_response, behavior_response, formatted_chat)

        ### ✅ Step 7: Get Higher Intelligence Pursuit Analysis ###
        intelligence_pursuit_response = process_higher_intelligence_pursuit_assistant(rmw_response, behavior_response, formatted_chat)

        ### ✅ Step 8: Get Self-Actualization Analysis ###
        self_actualization_response = process_self_actualization_assistant(rmw_response, behavior_response, formatted_chat)

        ### ✅ Step 9: Get STAD Analysis ###
        stad_response = process_stad_assistant(rmw_response, behavior_response, formatted_chat)

        ### ✅ Final Formatting ###
        rmw_response_cleaned = rmw_response.replace("{", "").replace("}", "")
        aux_response_cleaned = aux_response.replace("{", "").replace("}", "")
        blindspot_response_cleaned = blindspot_response.replace("{", "").replace("}", "")
        emotion_response_cleaned = emotion_response.replace("{", "").replace("}", "")
        intelligence_pursuit_response_cleaned = intelligence_pursuit_response.replace("{", "").replace("}", "")
        self_actualization_response_cleaned = self_actualization_response.replace("{", "").replace("}", "")
        stad_response_cleaned = stad_response.replace("{", "").replace("}", "")

        # Combine results from all assistants
        final_report = (
            f"📌 **RMW Analysis**:\n{rmw_response_cleaned}\n\n"
            f"📌 **Auxiliary Faculty Analysis**:\n{aux_response_cleaned}\n\n"
            f"📌 **Blindspot Analysis**:\n{blindspot_response_cleaned}\n\n"
            f"📌 **Emotion and Feeling Analysis**:\n{emotion_response_cleaned}\n\n"
            f"📌 **Higher Intelligence Pursuit Analysis**:\n{intelligence_pursuit_response_cleaned}\n\n"
            f"📌 **Self-Actualization Analysis**:\n{self_actualization_response_cleaned}\n\n"
            f"📌 **STAD Analysis**:\n{stad_response_cleaned}"
        )

        # ✅ Return final report including all assistant results
        return jsonify({"summary": final_report})

    except Exception as e:
        return jsonify({"error": str(e)}), 500








@app.route("/new_chat", methods=["POST"])
def new_chat():
    try:
        thread = ChatThread.query.first()
        if thread is not None:
            try:
                openai_client.beta.threads.delete(thread.thread_id)
            except openai.NotFoundError:
                pass
            db.session.delete(thread)
            db.session.commit()

        new_thread = openai_client.beta.threads.create()
        thread = ChatThread(thread_id=new_thread.id)
        db.session.add(thread)
        db.session.commit()

        return jsonify({"message": "New chat started!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

