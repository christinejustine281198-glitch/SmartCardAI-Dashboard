# backend/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class RunHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    script_name = db.Column(db.String(200))
    code = db.Column(db.Text)
    output = db.Column(db.Text)
    error = db.Column(db.Text)
    run_type = db.Column(db.String(50))  # manual / scheduled
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

