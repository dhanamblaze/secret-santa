from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import random, string

app = FastAPI()
rooms = {}

PAGE = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Secret Santa</title>
<style>
body{font-family:Arial;background:#ffeaea;margin:0;padding:20px}
.box{max-width:420px;margin:40px auto;background:#fff;padding:25px;border-radius:16px;box-shadow:0 8px 20px rgba(0,0,0,.15);text-align:center}
input{width:90%;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #ccc}
button{width:95%;padding:12px;margin:10px 0;background:#ff3b3b;color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:bold}
#out{margin-top:15px;word-break:break-all}
</style></head>
<body><div class="box">
<h2>🎅 Secret Santa</h2>
<input id="name" placeholder="Room name (optional)">
<input id="members" placeholder="Names comma la - dhanam, blaze, ram">
<button onclick="createRoom()">Create Room</button>
<div id="out"></div>
</div>
<script>
async function createRoom(){
  const membersRaw = document.getElementById('members').value.trim();
  const name = document.getElementById('name').value.trim() || 'MyRoom';
  if(!membersRaw){alert('Members podu da!');return;}
  const members = membersRaw.split(',').map(s=>s.trim()).filter(Boolean);
  if(members.length<2){alert('2 peru kooda venum da!');return;}
  document.getElementById('out').innerText='Creating...';
  const r = await fetch('/api/create-room',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,members})});
  const d = await r.json();
  if(d.error){document.getElementById('out').innerText=d.error;}
  else{document.getElementById('out').innerHTML='✅ Room Created!<br>Code: <b style=font-size:22px>'+d.code+'</b><br>Members: '+d.members.join(', ');}
}
</script></body></html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE

@app.post("/api/create-room")
def create_room(data: dict):
    members = data.get("members",[])
    name = data.get("name","Room")
    if len(members)<2:
        return {"error":"Need 2 members"}
    code=''.join(random.choices(string.ascii_uppercase+string.digits,k=6))
    rooms[code]={"name":name,"members":members}
    return {"code":code,"members":members}
