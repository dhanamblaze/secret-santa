from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import random, string, os

app = FastAPI()

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

rooms = {}

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/create-room")
async def create_room(data: dict):
    code = gen_code()
    name = data.get("name","").strip() or "Admin"
    rooms[code] = {"members": [name], "creator": name, "assigned": {}, "shuffled": False}
    return {"code": code}

@app.post("/api/join-room")
async def join_room(data: dict):
    code = data.get("code","").upper().strip()
    name = data.get("name","").strip()
    if not name:
        return {"error": "Enter name"}
    if code not in rooms:
        return {"error": "Room not found"}
    if name not in rooms[code]["members"]:
        rooms[code]["members"].append(name)
    return {"ok": True}

@app.get("/api/get-room")
async def get_room(code: str, name: str = ""):
    code = code.upper().strip()
    if code not in rooms:
        return {"error": "Room not found"}
    room = rooms[code]
    assigned = room["assigned"].get(name) if room["shuffled"] else None
    return {
        "members": room["members"],
        "creator": room["creator"],
        "is_creator": name == room["creator"],
        "assigned": assigned,
        "shuffled": room["shuffled"]
    }

@app.post("/api/shuffle-room")
async def shuffle_room(data: dict):
    code = data.get("code","").upper().strip()
    if code not in rooms:
        return {"error": "No room"}
    room = rooms[code]
    members = room["members"][:]
    if len(members) < 2:
        return {"error": "Need at least 2 members"}
    shuffled = members[:]
    while True:
        random.shuffle(shuffled)
        if all(a!=b for a,b in zip(members, shuffled)):
            break
    room["assigned"] = dict(zip(members, shuffled))
    room["shuffled"] = True
    return {"ok": True}
