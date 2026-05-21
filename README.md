# Dofbot AI Controller

An AI-powered robot arm controller that accepts natural language commands. You type something like "pick up from front" and the arm physically moves — no manual scripting required.

Built by Mariam Nadeem as part of an ECE Senior Project at Cal Poly Pomona, advised by Dr. Formicola.

---

## How it works

When you type a command, the Flask API sends it to Groq AI. Groq reads the verified movement library and picks which movements match your instruction. Flask then builds a Python script using the exact servo angles from that library and runs it on the Raspberry Pi. The arm moves.

The key design decision is that Groq never writes servo angles itself — it only picks movement names. All angles were physically tested by hand and saved in movements.json. This prevents the AI from sending wrong or dangerous values to the arm.

---

## Setup

Clone the repo and install dependencies:

```bash
git clone https://github.com/mariam12-n/dofbot-ai-controller.git
cd dofbot-ai-controller
pip install -r requirements.txt
```

Create the database:

```bash
python3 setup.py
```

Open robot_controller_api.py and add your Groq API key. You can get one free at console.groq.com:

```python
GROQ_API_KEY = "your_key_here"
```

Run the API:

```bash
python3 robot_controller_api.py
```

Open your browser at http://localhost:5000.

---

## Simulation mode

If you do not have a Dofbot-Pi connected, the API runs in simulation mode automatically. All endpoints work the same way but servo commands are printed to the terminal instead of moving real hardware.

```
[INFO] Arm_Lib not found — running in SIMULATION mode
[SIM] MOVE  s1= 90  s2= 55  s3= 20  s4= 40  s5= 89  s6=  0  speed=3000
[SIM] MOVE  s1= 89  s2= 55  s3= 20  s4= 40  s5= 89  s6=180  speed=1000
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /status | API status and current mode |
| GET | /movements | List all movements from movements.json |
| GET | /commands | List saved commands from the database |
| POST | /ai | Send a natural language instruction |
| POST | /move | Run a specific movement by name |
| POST | /run | Run a saved database command |
| POST | /save_command | Save a command to the database |

Example:

```bash
curl -X POST http://localhost:5000/ai \
  -H "Content-Type: application/json" \
  -d '{"instruction": "pick up from front", "groq_key": "your_key"}'
```

---

## Movement library

All 17 positions were physically tested on the real arm. You can add your own by editing movements.json — no code changes needed.

| Movement | Description |
|---|---|
| home | Return to home position |
| look left, look right | Rotate base |
| look up, look down | Tilt arm |
| point left, point right | Extend and point |
| pick up | Pick up from front |
| pick up left, pick up right | Pick up from side |
| put left, put right, put front | Place object |
| celebrate | Raise arm and clap gripper |
| yes | Nod up and down |
| no | Shake left and right |
| infront | Scan left and right |

---

## Hardware

- Yahboom Dofbot-Pi robot arm
- Raspberry Pi 5
- USB camera (optional)

The Arm_Lib SDK comes pre-installed with the Dofbot-Pi. More information at yahboom.net/study/Dofbot-Pi.

---

## Project structure

```
dofbot-ai-controller/
├── robot_controller_api.py   — Flask REST API
├── robot_web_ui.html         — Web interface
├── movements.json            — Verified servo positions
├── setup.py                  — First-time database setup
├── requirements.txt          — Python dependencies
└── docs/                     — Diagrams and screenshots
```

---

## License

MIT License
