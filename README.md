# 🎅 Christmas Chris Permanent - Secret Santa Website 🎄

A permanent, modern, mobile-responsive Secret Santa web application built with **FastAPI**, **SQLite**, and vanilla **HTML/CSS/JS**.

Designed for permanent production deployment on **Render**, **Railway**, **Fly.io**, or **Vercel** with zero temporary tunnels (no trycloudflare) and no hardcoded logins!

---

## ✨ Key Features

1. **No Hardcoded Login**:
   - `dhana/dhana1234` is completely gone.
   - Any user can register their own unique username and password.

2. **Special Character Password Support**:
   - Accepts complex passwords containing special characters (e.g. `Anu@2346`, `Test@123`, `my#pass$`, `@#$%^&*!_-`).
   - Securely hashed using salt-hashed **bcrypt**.

3. **Core Secret Santa Experience**:
   - **Page 1: Signup** with confirm password & special character support.
   - **Page 2: Login** with session tokens.
   - **Page 3: Dashboard** showing your joined groups, "Create New Group", and "Join Group via Code".
   - **Page 4: Group Page**:
     - View all group members and their wishlists.
     - Add and edit your own wishlist.
     - **Secret Santa Shuffle**: Derangement algorithm ensures nobody gets themselves!
     - **Secret Santa Assignment Card**: Displays your assigned recipient and their wishlist while keeping who is gifting to you completely secret!
     - 1-Click invite code copying.

4. **Production & Deployment Ready**:
   - Reads `$PORT` from environment variables automatically (default `8000`).
   - Full CORS support enabled (`CORSMiddleware`).
   - Static files served directly from `/static` and root `/`.
   - Includes `render.yaml` for 1-click Render blueprint deployment.

---

## 🚀 Running Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python main.py
```
Or with uvicorn directly:
```bash
uvicorn main:app --reload --port 8000
```

### 3. Open in Browser
Visit [http://localhost:8000](http://localhost:8000)

---

## 🌐 Deploying to Render (Permanent Free Hosting)

1. Push this folder to a GitHub repository.
2. Go to [Render.com](https://render.com) and click **New +** -> **Blueprint** (or **Web Service**).
3. Connect your GitHub repository:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Deploy! Your website will have a permanent `.onrender.com` URL (e.g., `https://christmas-chris.onrender.com`).

---

## 📁 Project Structure

```
christmas-chris-permanent/
├── main.py              # FastAPI app, SQLite database, auth & Secret Santa logic
├── requirements.txt     # Python dependencies
├── render.yaml          # Render deployment blueprint
├── Procfile             # Process file for cloud hosts
├── users.db             # Auto-generated SQLite database (created on first run)
├── static/
│   ├── index.html       # Single-Page UI with 4 views (Signup, Login, Dashboard, Group)
│   ├── style.css        # Festive Christmas theme (red/green/gold, snowflakes, responsive)
│   └── script.js        # State management, API calls, shuffle logic, toast alerts
└── README.md
```
