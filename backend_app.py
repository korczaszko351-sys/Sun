from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import jwt
import datetime
import bcrypt
import os
from functools import wraps
from sqlalchemy import or_

app = Flask(__name__)

# ================= CONFIG =================

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///school.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

SECRET = os.getenv("SECRET_KEY", "CHANGE_ME_SECRET")

db = SQLAlchemy(app)


# ================= MODELS =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.LargeBinary, nullable=False)
    role = db.Column(db.String(20), nullable=False)


class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    subject = db.Column(db.String(50))
    value = db.Column(db.String(10))


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    status = db.Column(db.String(20))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.Integer)
    receiver = db.Column(db.Integer)
    text = db.Column(db.Text)


# ================= INIT =================

with app.app_context():
    db.create_all()

    if not User.query.filter_by(login="admin").first():
        pw = bcrypt.hashpw("admin".encode(), bcrypt.gensalt())
        db.session.add(User(login="admin", password=pw, role="ADMIN"))
        db.session.commit()


# ================= SECURITY =================

def login_required(role=None):
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):

            token = request.headers.get("Authorization")

            if not token:
                return {"error": "no token"}, 401

            try:
                data = jwt.decode(token, SECRET, algorithms=["HS256"])
            except:
                return {"error": "invalid token"}, 401

            if role and data["role"] != role:
                return {"error": "forbidden"}, 403

            return fn(data, *args, **kwargs)

        return decorated
    return wrapper


# ================= JWT =================

def create_access(user):
    return jwt.encode({
        "id": user.id,
        "role": user.role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    }, SECRET, algorithm="HS256")


def create_refresh(user):
    return jwt.encode({
        "id": user.id,
        "type": "refresh",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, SECRET, algorithm="HS256")


# ================= ROOT (NO 404) =================

@app.get("/")
def home():
    return {
        "status": "OK",
        "name": "School API PRO",
        "version": "1.0",
        "routes": [
            "/login",
            "/users",
            "/grades/<id>",
            "/attendance/<id>",
            "/messages/<id>",
            "/health"
        ]
    }


# ================= HEALTH =================

@app.get("/health")
def health():
    return {
        "status": "online",
        "database": "sqlite",
        "auth": "jwt"
    }


# ================= LOGIN =================

@app.post("/login")
def login():

    data = request.json

    user = User.query.filter_by(login=data.get("login")).first()

    if not user:
        return {"error": "no user"}, 401

    if not bcrypt.checkpw(data.get("password", "").encode(), user.password):
        return {"error": "bad password"}, 401

    return {
        "access": create_access(user),
        "refresh": create_refresh(user),
        "user": {
            "id": user.id,
            "login": user.login,
            "role": user.role
        }
    }


# ================= USERS =================

@app.get("/users")
@login_required("ADMIN")
def users(current):
    return jsonify([
        {"id": u.id, "login": u.login, "role": u.role}
        for u in User.query.all()
    ])


@app.post("/users")
@login_required("ADMIN")
def add_user(current):

    d = request.json

    pw = bcrypt.hashpw(d["password"].encode(), bcrypt.gensalt())

    db.session.add(User(
        login=d["login"],
        password=pw,
        role=d["role"]
    ))

    db.session.commit()

    return {"ok": True}


# ================= GRADES =================

@app.get("/grades/<int:sid>")
@login_required()
def grades(current, sid):

    if current["role"] not in ["ADMIN", "TEACHER"] and current["id"] != sid:
        return {"error": "no access"}, 403

    data = Grade.query.filter_by(student_id=sid).all()

    return jsonify([
        {"id": g.id, "subject": g.subject, "value": g.value}
        for g in data
    ])


@app.post("/grades")
@login_required("TEACHER")
def add_grade(current):

    d = request.json

    db.session.add(Grade(
        student_id=d["student_id"],
        subject=d["subject"],
        value=d["value"]
    ))

    db.session.commit()

    return {"ok": True}


# ================= ATTENDANCE =================

@app.get("/attendance/<int:sid>")
@login_required()
def att(current, sid):

    if current["role"] not in ["ADMIN", "TEACHER"] and current["id"] != sid:
        return {"error": "no access"}, 403

    data = Attendance.query.filter_by(student_id=sid).all()

    return jsonify([
        {"id": a.id, "status": a.status}
        for a in data
    ])


@app.post("/attendance")
@login_required("TEACHER")
def add_att(current):

    d = request.json

    db.session.add(Attendance(
        student_id=d["student_id"],
        status=d["status"]
    ))

    db.session.commit()

    return {"ok": True}


# ================= MESSAGES =================

@app.get("/messages/<int:uid>")
@login_required()
def messages(current, uid):

    if current["id"] != uid and current["role"] != "ADMIN":
        return {"error": "no access"}, 403

    data = Message.query.filter(
        or_(Message.sender == uid, Message.receiver == uid)
    ).all()

    return jsonify([
        {
            "id": m.id,
            "sender": m.sender,
            "receiver": m.receiver,
            "text": m.text
        }
        for m in data
    ])


@app.post("/messages")
@login_required()
def send_msg(current):

    d = request.json

    db.session.add(Message(
        sender=current["id"],
        receiver=d["to"],
        text=d["text"]
    ))

    db.session.commit()

    return {"ok": True}


# ================= 404 HANDLER =================

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "endpoint not found",
        "hint": "use / to see API routes"
    }), 404


# ================= RUN =================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )