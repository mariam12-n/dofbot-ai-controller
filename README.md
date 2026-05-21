# 🤖 Dofbot AI Controller

AI-powered robot arm controller using natural language commands.  
Type **"pick up from front"** and the arm physically moves — no manual scripting required.

Built by **Mariam Nadeem** — Cal Poly Pomona, ECE Senior Project  
Advisor: Dr. Formicola

---

## Demo

![Robot Arm Demo](docs/IMG_2616_HD.jpg)

---

## How It Works

```
You type "pick up from front"
        ↓
Flask API receives the command
        ↓
Groq AI picks movements from the verified library
        ↓
Python script is generated with exact servo angles
        ↓
🦾 Robot arm physically moves
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend API | Flask (Python) |
| AI Model | Groq — LLaMA 3.1 8B |
| Movement Library | movements.json (17 verified positions) |
| Database | SQLite |
| Hardware | Yahboom Dofbot-Pi + Raspberry Pi 5 |
| Servo Control | Arm_Lib via UART |

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/mariam12-n/dofbot-ai-controller.git
cd dofbot-ai-controller
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up the database
```bash
python3 setup.py
```

### 4. Add your Groq API key
Open `robot_controller_api.py` and replace:
```python
GROQ_API_KEY = "your_groq_api_key_here"
```
Get a free key at [console.groq.com](https://console.groq.com)

### 5. Run the API
```bash
python3 robot_controller_api.py
```

### 6. Open the web UI
```
http://localhost:5000
```

---

## Simulation Mode

**No robot arm? No problem.**  
If `Arm_Lib` is not found (no hardware connected), the API automatically runs in **simulation mode** — all endpoints work normally and servo commands are printed to the terminal instead of moving a real arm.

```
[INFO] Arm_Lib not found — running in SIMULATION mode
[SIM] MOVE  s1= 90  s2= 55  s3= 20  s4= 40  s5= 89  s6=  0  speed=3000
[SIM] MOVE  s1= 89  s2= 55  s3= 20  s4= 40  s5= 89  s6=180  speed=1000
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/status` | API status + hardware/simulation mode |
| GET | `/movements` | List all 17 movements from movements.json |
| GET | `/commands` | List saved commands from database |
| POST | `/ai` | Natural language → Groq AI → arm moves |
| POST | `/move` | Run a specific movement by name |
| POST | `/run` | Run a saved database command |
| POST | `/save_command` | Save a command to the database |

### Example — control the arm via curl
```bash
# Ask the arm to pick up an object
curl -X POST http://localhost:5000/ai \
  -H "Content-Type: application/json" \
  -d '{"instruction": "pick up from front", "groq_key": "your_key"}'

# Run a specific movement directly
curl -X POST http://localhost:5000/move \
  -H "Content-Type: application/json" \
  -d '{"movement": "yes"}'
```

---

## Movement Library

All 17 positions were **physically tested** on the real arm by hand.  
Groq AI only picks movement names — it never writes servo angles itself.  
Edit `movements.json` to add your own positions.

| Movement | Description |
|---|---|
| home | Return to home position |
| look left / right | Rotate base left or right |
| look up / down | Tilt arm up or down |
| point left / right | Extend and point |
| pick up | Pick up object from front |
| pick up left / right | Pick up from side |
| put left / right / front | Place object in direction |
| celebrate | Raise arm and clap gripper |
| yes | Nod up and down |
| no | Shake left and right |
| infront | Scan left and right |

---

## Hardware Required

- Yahboom Dofbot-Pi robot arm
- Raspberry Pi 5
- USB camera (optional)

The `Arm_Lib` SDK comes pre-installed with the Yahboom Dofbot-Pi.  
More info: [yahboom.net/study/Dofbot-Pi](https://www.yahboom.net/study/Dofbot-Pi)

---

## Project Structure

```
dofbot-ai-controller/
├── robot_controller_api.py   # Flask REST API — main backend
├── robot_web_ui.html         # Web interface
├── movements.json            # 17 verified servo positions
├── setup.py                  # First-time database setup
├── requirements.txt          # Python dependencies
└── docs/                     # Diagrams and screenshots
```

---

## License

MIT License — free to use and modify.
