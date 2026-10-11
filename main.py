from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import random, string

app = FastAPI()
rooms = {}

PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Secret Santa Pro</title>
<style>
body{font-family:Arial;background:#ffe6e6;margin:0;padding:15px}
.card{max-width:450px;margin:20px auto;background:white;padding:20px;border-radius:18px;box-shadow:0 8px 25px rgba(0,0,0,.15);text-align:center}
input,button{width:92%;padding:12px;margin:8px 0;border-radius:10px;border:1px solid #ccc;font-size:15px}
button{background:#ff3b3b;color:white;border:none;font-weight:bold;cursor:pointer}
button:disabled{background:#aaa}
button:hover{background:#e60000}
.member{background:#f8f8f8;padding:8px;margin:4px;border-radius:8px;text-align:left}
.gift{font-size:70px;cursor:pointer;transition:.3s}
.gift:hover{transform:scale(1.2)}
.hidden{display:none}
.codebox{background:#fff3cd;padding:12px;border-radius:10px;font-size:22px;letter-spacing:3px;font-weight:bold;margin:10px 0;border:2px dashed #ff3b3b}
</style>
</head>
<body>

<div id="loginSec" class="card">
<h2>🎅 Secret Santa</h2>
<input id="userName" placeholder="Name">
<button onclick="login()">Login</button>
</div>

<div id="dashSec" class="card hidden">
<h2>Hi <span id="hiName"></span>! 👋</h2>
<button onclick="createRoom()">🎁 Create Room</button>
<p>OR</p>
<input id="joinCode" placeholder="Room Code">
<button onclick="joinRoom()">🚪 Join Room</button>
<div id="dashMsg"></div>
</div>

<div id="roomSec" class="card hidden">
<h3>Room Code:</h3>
<div id="roomCode" class="codebox"></div>
<button onclick="copyCode()">Copy Code & Share</button>
<h4>Joined Members (<span id="memCount">0</span>):</h4>
<div id="memberList"></div>
<div id="creatorCtrl" class="hidden">
<button id="shuffleBtn" onclick="shuffleRoom()" style="margin-top:15px">🔀 Shuffle Names</button>
</div>
<div id="giftArea" class="hidden">
<hr>
<div class="gift" onclick="openGift()">🎁</div>
<div id="myAssignment" style="font-size:36px;font-weight:bold;margin-top:15px"></div>
</div>
<div id="roomMsg"></div>
<button onclick="location.reload()" style="background:#666;margin-top:15px">Leave Room</button>
</div>

<script>
let myName="", myCode="", isCreator=false, interval=null;

function login(){
  let n=document.getElementById('userName').value.trim();
  if(!n){alert('Name podu da!');return;}
  myName=n; localStorage.setItem('santaName',n);
  document.getElementById('loginSec').classList.add('hidden');
  document.getElementById('dashSec').classList.remove('hidden');
  document.getElementById('hiName').innerText=myName;
}
let saved=localStorage.getItem('santaName');
if(saved){document.getElementById('userName').value=saved;}

async function createRoom(){
  document.getElementById('dashMsg').innerText='Creating...';
  let r=await fetch('/api/create-room',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({creator:myName})});
  let d=await r.json();
  if(d.error){document.getElementById('dashMsg').innerText=d.error;return;}
  enterRoom(d.code,true);
}

async function joinRoom(){
  let code=document.getElementById('joinCode').value.trim().toUpperCase();
  if(!code){alert('Code podu da!');return;}
  let r=await fetch('/api/join-room',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code,name:myName})});
  let d=await r.json();
  if(d.error){document.getElementById('dashMsg').innerText=d.error;return;}
  enterRoom(code,false);
}

function enterRoom(code, creator){
  myCode=code; isCreator=creator;
  document.getElementById('dashSec').classList.add('hidden');
  document.getElementById('roomSec').classList.remove('hidden');
  document.getElementById('roomCode').innerText=code;
  startPolling();
}

function startPolling(){
  loadRoom();
  if(interval) clearInterval(interval);
  interval=setInterval(loadRoom,3000);
}

async function loadRoom(){
  let r=await fetch('/api/room/'+myCode);
  let d=await r.json();
  if(d.error){document.getElementById('roomMsg').innerText=d.error;return;}
  document.getElementById('memCount').innerText=d.members.length;
  document.getElementById('memberList').innerHTML=d.members.map(m=>`<div class="member">${m==d.creator?'👑 ':''}${m} ${m==myName?'(You)':''}</div>`).join('');
  if(myName==d.creator){
    document.getElementById('creatorCtrl').classList.remove('hidden');
    isCreator=true;
    document.getElementById('shuffleBtn').disabled = d.members.length<2 || d.shuffled;
    if(d.shuffled) document.getElementById('shuffleBtn').innerText='✅ Shuffled Done';
  }
  if(d.shuffled){
    document.getElementById('giftArea').classList.remove('hidden');
    document.getElementById('creatorCtrl').classList.add('hidden');
  }
}

async function shuffleRoom(){
  let r=await fetch('/api/shuffle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:myCode,creator:myName})});
  let d=await r.json();
  if(d.error){alert(d.error);return;}
  loadRoom();
}

async function openGift(){
  let r=await fetch(`/api/my-assignment/${myCode}/${encodeURIComponent(myName)}`);
  let d=await r.json();
  if(d.error){alert(d.error);return;}
  document.getElementById('myAssignment').innerHTML=`${d.to} 🩷💙`;
  document.querySelector('.gift').innerText='🎉';
}

function copyCode(){
  navigator.clipboard.writeText(myCode);
  alert('Code copied: '+myCode);
}
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE

@app.post("/api/create-room")
def create_room(data: dict):
    creator = data.get("creator","").strip()
    if not creator:
        return {"error":"Name venum da"}
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    while code in rooms:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    rooms[code] = {"creator": creator, "members": [creator], "assigned": {}, "shuffled": False}
    return {"code": code}

@app.post("/api/join-room")
def join_room(data: dict):
    code = data.get("code","").upper().strip()
    name = data.get("name","").strip()
    if code not in rooms:
        return {"error":"Room code thappu da!"}
    room = rooms[code]
    if room["shuffled"]:
        if name not in room["members"]:
            return {"error":"Already shuffled da, ippo join panna mudiyathu!"}
    else:
        if name not in room["members"]:
            room["members"].append(name)
    return {"ok": True}

@app.get("/api/room/{code}")
def get_room(code: str):
    code=code.upper().strip()
    if code not in rooms:
        return {"error":"Room illa da"}
    r=rooms[code]
    return {"creator": r["creator"], "members": r["members"], "shuffled": r["shuffled"]}

@app.post("/api/shuffle")
def shuffle_room(data: dict):
    code=data.get("code","").upper().strip()
    creator=data.get("creator","").strip()
    if code not in rooms:
        return {"error":"Room illa"}
    room=rooms[code]
    if room["creator"]!=creator:
        return {"error":"Only creator can shuffle da!"}
    if len(room["members"])<2:
        return {"error":"2 peru kooda venum da!"}
    members=room["members"][:]
    shuffled=members[:]
    for _ in range(1000):
        random.shuffle(shuffled)
        if all(a!=b for a,b in zip(members, shuffled)):
            break
    room["assigned"]=dict(zip(members, shuffled))
    room["shuffled"]=True
    return {"ok":True}

@app.get("/api/my-assignment/{code}/{name}")
def my_assignment(code: str, name: str):
    code=code.upper().strip()
    if code not in rooms:
        return {"error":"Room illa"}
    room=rooms[code]
    if not room["shuffled"]:
        return {"error":"Innum shuffle pannala da!"}
    if name not in room["assigned"]:
        return {"error":"Neenga room la illa da"}
    return {"to": room["assigned"][name]}
