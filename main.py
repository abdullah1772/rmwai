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
blindspt_assistant_id = "asst_HowmEO015nb7cOwc2K1TnhlH"
Emotion_and_feeling_assistant_id = "asst_vXcEIHkBuhhRZL7w0PFfjMb6"
Higher_Intelligence_Pursuit_assistant_id = "asst_SoMKjSJIYJQGlAWqa7PNH4O4"
self_actualization_assistant_id = "asst_wY8Qf822dtUlBsGAM5vwJtyT"
stad_assistant_id = "asst_KpXdl3ETnxVT6NasbqZ3pJr4"


MAX_QUESTIONS = 10  # Limit on follow-up questions

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

        ### ✅ Step 1: Behavior Identification Assistant Processing ###
        # Create a new temporary thread for Behavior Identification Assistant
        temp_behavior_thread = openai_client.beta.threads.create()
        behavior_thread_id = temp_behavior_thread.id  

        # Send chat history to Behavior Identification Assistant
        openai_client.beta.threads.messages.create(
            thread_id=behavior_thread_id,
            role="user",
            content=f"Here is the conversation history:\n{formatted_chat}"
        )

        # Run behavior analysis
        behavior_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=behavior_thread_id,
            assistant_id=behavior_assistant_id,
            instructions="Analyze the user's behavior based on the provided conversation history and provide insights."
        )

        if behavior_analysis_run.status == 'completed':
            behavior_messages = openai_client.beta.threads.messages.list(thread_id=behavior_thread_id)
            behavior_response = behavior_messages.data[0].content[0].text.value  # Extract analysis
        else:
            behavior_response = "Error generating behavior analysis report."

        # ✅ Delete the temporary thread for Behavior Identification Assistant
        openai_client.beta.threads.delete(thread_id=behavior_thread_id)

        ### ✅ Step 2: Extract Follow-Up Questions ###
        follow_up_questions = [
            msg.content[0].text.value for msg in messages.data if msg.role == "assistant"
        ]
        follow_up_text = "\n".join(follow_up_questions)

        ### ✅ Step 3: RMW Assistant Processing ###
        # Create a new temporary thread for RMW Assistant
        temp_rmw_thread = openai_client.beta.threads.create()
        rmw_thread_id = temp_rmw_thread.id  

        # Send follow-up questions + behavior response to RMW Assistant
        openai_client.beta.threads.messages.create(
            thread_id=rmw_thread_id,
            role="user",
            content=f"Follow-up questions:\n{follow_up_text}\n\nBehavior Analysis:\n{behavior_response}"
        )

        # Run RMW analysis
        rmw_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=rmw_thread_id,
            assistant_id=rmw_assistant_id,
            instructions=""
        )

        if rmw_analysis_run.status == 'completed':
            rmw_messages = openai_client.beta.threads.messages.list(thread_id=rmw_thread_id)
            rmw_response = rmw_messages.data[0].content[0].text.value  # Extract response
        else:
            rmw_response = "Error generating RMW analysis report."

        # ✅ Delete the temporary thread for RMW Assistant
        openai_client.beta.threads.delete(thread_id=rmw_thread_id)

        ### ✅ Step 4: AUXILIARY FACULTY Assistant Processing ###
        # Create a new temporary thread for AUXILIARY FACULTY Assistant
        temp_aux_thread = openai_client.beta.threads.create()
        aux_thread_id = temp_aux_thread.id  

        # Send chat history + behavior patterns to AUXILIARY FACULTY Assistant
        openai_client.beta.threads.messages.create(
            thread_id=aux_thread_id,
            role="user",
            content=f"Chat History:\n{formatted_chat}\n\nBehavior Patterns:\n{behavior_response}"
        )

        # Run AUXILIARY analysis
        aux_analysis_run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=aux_thread_id,
            assistant_id=aux_assistant_id,
            instructions=""
        )

        if aux_analysis_run.status == 'completed':
            aux_messages = openai_client.beta.threads.messages.list(thread_id=aux_thread_id)
            aux_response = aux_messages.data[0].content[0].text.value  # Extract response
        else:
            aux_response = "Error generating Auxiliary Faculty analysis report."

        # ✅ Delete the temporary thread for AUXILIARY FACULTY Assistant
        openai_client.beta.threads.delete(thread_id=aux_thread_id)

        ### ✅ Final Formatting ###
        rmw_response_cleaned = rmw_response.replace("{", "").replace("}", "")
        aux_response_cleaned = aux_response.replace("{", "").replace("}", "")

        # Combine results from both assistants
        final_report = (
            f"📌 **RMW Analysis**:\n{rmw_response_cleaned}\n\n"
            f"📌 **Auxiliary Faculty Analysis**:\n{aux_response_cleaned}"
        )

        # ✅ Return final report including both RMW and AUXILIARY FACULTY assistant results
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

if __name__ == '__main__':
    app.run(debug=True)
