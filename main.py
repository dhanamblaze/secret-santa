from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import random, string, os

app = FastAPI()

# static folder mount pannurom - ithu than bg.jpg ku mukkiyam
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

rooms = {}
users = {}

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, code: str = ""):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/login")
async def login(data: dict):
    name = data.get("name","").strip()
    users[name] = True
    return {"ok": True}

@app.post("/api/create-room")
async def create_room(data: dict):
    code = gen_code()
    rooms[code] = {"members": [], "creator": "", "assigned": {}, "shuffled": False}
    return {"code": code}

@app.post("/api/join-room")
async def join_room(data: dict):
    code = data.get("code","").upper()
    name = data.get("name") or list(users.keys())[-1] if users else "User"
    # frontend la name localStorage la irukku, so namma last login edukkrom
    if code not in rooms:
        return {"error": "Room not found"}
    # Avoid duplicate
    # We'll get name from request via a simple trick - use first member if not given
    # Actually we will use the name stored in users
    # For simplicity, get from headers? We'll just expect client to send name via localStorage logic in backend we handle differently

    # Hack: get last logged in user
    last_user = list(users.keys())[-1] if users else "Guest"
    if last_user not in rooms[code]["members"]:
        rooms[code]["members"].append(last_user)
        if not rooms[code]["creator"]:
            rooms[code]["creator"] = last_user
    return {"ok": True}

# Better join with name
@app.post("/api/join-room-v2")
async def join_room_v2(data: dict):
    code = data.get("code","").upper()
    name = data.get("name","")
    if code not in rooms:
        return {"error": "No room"}
    if name not in rooms[code]["members"]:
        rooms[code]["members"].append(name)
        if not rooms[code]["creator"]:
            rooms[code]["creator"] = name
    return {"ok": True}

# Override to handle both
@app.post("/api/join-room")
async def join_room_final(data: dict):
    code = data.get("code","").upper()
    # try to get name from data or last user
    name = data.get("name") or (list(users.keys())[-1] if users else "")
    if code not in rooms:
        return {"error": "Room not found"}
    if name and name not in rooms[code]["members"]:
        rooms[code]["members"].append(name)
        if not rooms[code]["creator"]:
            rooms[code]["creator"] = name
    return {"ok": True}

@app.get("/api/get-room")
async def get_room(code: str, name: str = ""):
    code = code.upper()
    if code not in rooms:
        return {"error": "Room not found"}
    room = rooms[code]
    # get last user as current user if not passed
    current = list(users.keys())[-1] if users else ""
    # check query param for name
    if name:
        current = name

    # Find assigned if shuffled
    assigned = None
    if room["shuffled"]:
        assigned = room["assigned"].get(current)

    # Try to find assigned by checking all if current not found (for simplicity)
    if not assigned and room["shuffled"] and current in room["assigned"]:
        assigned = room["assigned"][current]

    return {
        "members": room["members"],
        "creator": room["creator"],
        "is_creator": current == room["creator"],
        "assigned": assigned,
        "shuffled": room["shuffled"]
    }

@app.post("/api/shuffle-room")
async def shuffle_room(data: dict):
    code = data.get("code","").upper()
    if code not in rooms:
        return {"error": "No room"}
    room = rooms[code]
    members = room["members"][:]
    if len(members) < 2:
        return {"error": "Need 2 members"}
    # shuffle until no one gets self
    shuffled = members[:]
    while True:
        random.shuffle(shuffled)
        if all(a!=b for a,b in zip(members, shuffled)):
            break
    room["assigned"] = dict(zip(members, shuffled))
    room["shuffled"] = True
    return {"ok": True}
