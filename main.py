from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import datetime
import random

app = Flask(__name__)
CORS(app)

app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "postgresql://postgres:Vinay%40121@localhost/QueryRaisedDB"
db = SQLAlchemy(app)

# Initialize SocketIO
socketio = SocketIO(app)


# Store users
users = {}
# in this format, users are stored:- "{'g2-LvFRnFyDBj9nwAAAJ': {'name': 'binod', 'isAdmin': False}}"

# Store admin rooms
# admin-rooms = set()


# Sample data (replace this with your actual data)
crop_options = ["Rice", "RicePB", "Paddy", "Wheat"]

scan_options = [
    {
        "id": i,
        "ScanId": f"{random.choice(crop_options)}-1423-{i}",
        "date": (datetime.datetime.now() + datetime.timedelta(days=i)).strftime(
            "%Y-%m-%d"
        ),
        "crop": random.choice(crop_options),
    }
    for i in range(1, 201)
]


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    description = db.Column(db.String(250))
    issue_type = db.Column(db.String)
    scans = db.Column(db.String)


@app.route("/save_ticket", methods=["POST"])
def save_ticket():
    try:
        # Extract form data
        title = request.form["title"]
        description = request.form["description"]
        issue_type = request.form["issue-type"]
        scans = request.form["scans"]

        # Create Ticket object
        new_ticket = Ticket(
            title=title, description=description, issue_type=issue_type, scans=scans
        )

        # Save to the database
        db.session.add(new_ticket)
        db.session.commit()

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"message": "Error occurred while processing the request"}), 500

    return jsonify({"message": "Ticket saved successfully"}), 200


# route to scan data id and date
@app.route("/get_scan_options", methods=["GET"])
def get_scan_options():
    return jsonify(scan_options)


@app.route("/ticket")
def ticket():
    return render_template("Ticket.html")


@app.route("/")
def support():
    return render_template("chat.html")


# different sockets handling
@socketio.on("connect")
def handle_connection():
    print("Client connected")


@socketio.on("new-user-joined")
def handle_new_user_joined(data):
    if data["isAdmin"]:
        join_room("admin-room")
    else:
        users[request.sid] = {"name": data["name"]}
        join_room("user-room-" + data["name"])  # Each user has their own room
        socketio.emit("user-joined", data["name"], room="admin-room")


@socketio.on("admin-send")
def handle_admin_send(data):
    admin_name = data["adminName"]
    target_user = data["targetUser"]
    message = data["message"]

    # Emit the admin message directly to the target user's room
    socketio.emit(
        "admin-message",
        {"admin": admin_name, "message": message},
        room="user-room-" + target_user,
        namespace="/",
    )


@socketio.on("user-send")
def handle_user_send(data):
    user_name = data["userName"]
    message = data["message"]
    socketio.emit("receive", {"message": message, "user": user_name}, room="admin-room")


@socketio.on("disconnect")
def handle_disconnect():
    user_info = request.sid
    print(user_info)
    if f"{user_info}@admin-room" in socketio.server.manager.rooms:
        leave_room(f"{user_info}@admin-room")
    else:
        # Assuming user names have no spaces, you might need a better way to extract the name
        user_name = users[user_info]['name']
        print(user_name)
        leave_room(f"user-room-{user_name}")
        socketio.emit("left", {"user_name": user_name}, room="admin-room")
    print("Client disconnected")


if __name__ == "__main__":
    socketio.run(app, debug=True)
