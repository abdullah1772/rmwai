from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ChatThread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(128), unique=True, nullable=False)
