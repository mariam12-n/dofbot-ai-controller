"""
robot_controller_api.py
-----------------------
Smart Flask API for Yahboom Dofbot-Pi robot arm.
Supports SIMULATION MODE when hardware is not connected.

Movements are loaded from movements.json — edit that file to add
or change positions without touching this code.

Endpoints:
  GET  /status      -> API status + mode (real or simulation)
  GET  /commands    -> list saved DB commands
  GET  /movements   -> list all movements from movements.json
  POST /run         -> run a saved DB command
  POST /move        -> run a library movement by name
  POST /ai          -> Groq AI chains library movements
  POST /save_command-> save a command to SQLite
"""

import sys, os, sqlite3, requests, json, time
from flask import Flask, request, jsonify

# ---------------------------
# Configuration
# ---------------------------
SCRIPT_PATH   = "/home/nadeem/dofbot-Pi/10.Basic control course"
DB            = "/home/nadeem/robot_actions.db"
GROQ_API_KEY  = "your_groq_api_key_here"   # replace with your key from console.groq.com
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = "llama-3.1-8b-instant"
GENERATED_DIR = "/home/nadeem/generated_scripts"

# movements.json lives in the same folder as this script
MOVEMENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "movements.json")

os.makedirs(GENERATED_DIR, exist_ok=True)

# ---------------------------
# Load movements from JSON
# ---------------------------
def load_movements():
    """
    Load the movement library from movements.json.
    If the file is missing, fall back to a single 'home' movement
    so the API still starts without crashing.
    """
    if not os.path.exists(MOVEMENTS_FILE):
        print(f"[WARN] movements.json not found at {MOVEMENTS_FILE}")
        print("[WARN] Only 'home' movement available. Add movements.json to enable the full library.")
        return {
            "home": {
                "description": "Return arm to home position (straight up)",
                "steps": [[90, 90, 90, 90, 90, 180, 3000, 2]]
            }
        }

    with open(MOVEMENTS_FILE, "r") as f:
        data = json.load(f)

    print(f"[INFO] Loaded {len(data)} movements from movements.json")
    return data

MOVEMENTS = load_movements()

# ---------------------------
# Arm_Lib: real or simulated
# ---------------------------
try:
    if SCRIPT_PATH not in sys.path:
        sys.path.insert(0, SCRIPT_PATH)
    from Arm_Lib import Arm_Device
    SIMULATION_MODE = False
    print("[INFO] Arm_Lib loaded — running in HARDWARE mode")
except ImportError:
    SIMULATION_MODE = True
    print("[INFO] Arm_Lib not found — running in SIMULATION mode")
    print("[INFO] All API endpoints work normally. Servo commands are logged instead of executed.")

    class Arm_Device:
        """Simulated robot arm — prints servo commands instead of moving hardware."""

        def Arm_serial_set_torque(self, state):
            print(f"  [SIM] Torque {'ON' if state else 'OFF'}")

        def Arm_serial_servo_write6(self, s1, s2, s3, s4, s5, s6, speed):
            print(f"  [SIM] MOVE  s1={s1:>3} s2={s2:>3} s3={s3:>3} "
                  f"s4={s4:>3} s5={s5:>3} s6={s6:>3}  speed={speed}")

        def Arm_serial_servo_read(self, servo_id):
            return 90

# ---------------------------
# Flask app
# ---------------------------
app = Flask(__name__)

# ---------------------------
# Core: build one combined script and run it
# ---------------------------
def build_and_run(movements_list):
    """
    Build a single Python script from a list of movement names,
    then execute it. In simulation mode the Arm_Device class
    just prints the commands instead of sending them to hardware.
    """
    all_steps = []
    holding   = False

    for name in movements_list:
        if name not in MOVEMENTS:
            print(f"[WARN] Unknown movement: '{name}' — not in movements.json, skipping")
            continue

        steps = MOVEMENTS[name]["steps"]

        # If arm is holding an object and home is called, keep gripper closed (S6=180)
        if name == "home" and holding:
            steps = [[s[0], s[1], s[2], s[3], s[4], 180, s[6], s[7]] for s in steps]

        all_steps.extend(steps)

        if "pick up" in name:
            holding = True
        if "put" in name:
            holding = False

    if not all_steps:
        return False, "No valid movements to execute — check movements.json", ""

    # Build the Python script
    lines = [
        "import sys, time",
        f"sys.path.append('{SCRIPT_PATH}')",
        "try:",
        "    from Arm_Lib import Arm_Device",
        "except ImportError:",
        "    class Arm_Device:",
        "        def Arm_serial_set_torque(self, s): print(f'  [SIM] Torque {\"ON\" if s else \"OFF\"}')",
        "        def Arm_serial_servo_write6(self, s1,s2,s3,s4,s5,s6,spd):",
        "            print(f'  [SIM] MOVE s1={s1} s2={s2} s3={s3} s4={s4} s5={s5} s6={s6} speed={spd}')",
        "",
        "Arm = Arm_Device()",
        "try:",
        "    Arm.Arm_serial_set_torque(True)",
    ]

    for s in all_steps:
        s1, s2, s3, s4, s5, s6, speed, sleep = s
        lines.append(
            f"    Arm.Arm_serial_servo_write6("
            f"{int(s1)},{int(s2)},{int(s3)},{int(s4)},{int(s5)},{int(s6)},{int(speed)})"
        )
        lines.append(f"    time.sleep({sleep})")

    lines += ["finally:", "    pass  # keep torque on so gripper holds object"]

    code = "\n".join(lines)

    # Save script to disk
    path = os.path.join(GENERATED_DIR, "gen_latest.py")
    with open(path, "w") as f:
        f.write(code)

    # Execute
    if SIMULATION_MODE:
        print(f"\n[SIM] Running movements: {movements_list}")
        exec(compile(code, path, "exec"), {})
        return True, "Simulated successfully", code
    else:
        exit_code = os.system(f"cd '{SCRIPT_PATH}' && python3 '{path}'")
        ok = exit_code == 0
        return ok, "Done!" if ok else f"Failed (exit {exit_code})", code

# ---------------------------
# Database helpers
# ---------------------------
def get_commands():
    try:
        conn = sqlite3.connect(DB)
        cur  = conn.cursor()
        cur.execute("SELECT command, action_function, description FROM actions")
        rows = cur.fetchall()
        conn.close()
        return rows
    except:
        return []

def run_saved(command):
    try:
        conn = sqlite3.connect(DB)
        cur  = conn.cursor()
        cur.execute("SELECT action_function FROM actions WHERE command=?", (command,))
        row  = cur.fetchone()
        conn.close()
    except Exception as e:
        return False, "DB error: " + str(e)
    if not row:
        return False, "Command not found: " + command
    path = os.path.join(SCRIPT_PATH, row[0])
    if not os.path.exists(path):
        return False, "Script file not found: " + path
    exit_code = os.system(f"cd '{SCRIPT_PATH}' && python3 '{path}'")
    return exit_code == 0, "Done" if exit_code == 0 else "Failed"

# ---------------------------
# Groq AI
# ---------------------------
def ask_groq(instruction, key):
    mv_list = "\n".join(
        f'- "{n}": {m["description"]}' for n, m in MOVEMENTS.items()
    )
    prompt = f"""You control a robot arm. Pick movements from this list and return ONLY a JSON array.

MOVEMENTS:
{mv_list}

RULES:
- Return ONLY a JSON array like ["pick up","home"]
- NEVER add "home" after pick up movements — arm stays holding the object
- Only release with put left/right/front when user says put/place/drop/release
- For look/celebrate/yes/no: end with "home"
- NEVER add movements the user did not ask for
- Return ONLY the JSON array, no explanation

EXAMPLES:
- "pick up from front" -> ["pick up"]
- "pick up and put left" -> ["pick up","put left"]
- "look left then right" -> ["look left","look right","home"]
- "say yes" -> ["yes","home"]
- "celebrate" -> ["celebrate","home"]
- "drop it" -> ["put front"]

User: {instruction}"""

    r = requests.post(
        GROQ_URL,
        json={
            "model":    GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens":  200
        },
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type":  "application/json"
        },
        timeout=30
    )
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"].strip()
    if "```" in raw:
        raw = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("```"))
    raw   = raw.strip()
    start = raw.find("[")
    end   = raw.rfind("]") + 1
    return json.loads(raw[start:end])

# ---------------------------
# Flask routes
# ---------------------------
@app.route("/")
def index():
    ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robot_web_ui.html")
    if os.path.exists(ui):
        with open(ui) as f:
            return f.read(), 200, {"Content-Type": "text/html"}
    return jsonify({"status": "running", "simulation": SIMULATION_MODE})

@app.route("/status")
def status():
    return jsonify({
        "status":           "online",
        "mode":             "simulation" if SIMULATION_MODE else "hardware",
        "movements_loaded": len(MOVEMENTS),
        "commands_loaded":  len(get_commands()),
        "movements_file":   MOVEMENTS_FILE
    })

@app.route("/commands")
def commands():
    rows = get_commands()
    return jsonify({
        "commands": [
            {"command": r[0], "function": r[1], "description": r[2]} for r in rows
        ]
    })

@app.route("/movements")
def movements():
    return jsonify({
        "source": MOVEMENTS_FILE,
        "movements": [
            {"name": n, "description": m["description"], "steps": len(m["steps"])}
            for n, m in MOVEMENTS.items()
        ]
    })

@app.route("/run", methods=["POST"])
def run():
    data = request.get_json()
    if not data or "command" not in data:
        return jsonify({"success": False, "message": "Missing 'command' field"}), 400
    ok, msg = run_saved(data["command"].strip())
    return jsonify({"success": ok, "command": data["command"], "message": msg})

@app.route("/move", methods=["POST"])
def move():
    data = request.get_json()
    if not data or "movement" not in data:
        return jsonify({"success": False, "message": "Missing 'movement' field"}), 400
    ok, msg, code = build_and_run([data["movement"].strip()])
    return jsonify({
        "success":  ok,
        "movement": data["movement"],
        "mode":     "simulation" if SIMULATION_MODE else "hardware",
        "message":  msg
    })

@app.route("/ai", methods=["POST"])
def ai():
    data = request.get_json()
    if not data or "instruction" not in data:
        return jsonify({"success": False, "message": "Missing 'instruction' field"}), 400

    instruction = data["instruction"].strip()
    key         = data.get("groq_key", "").strip() or GROQ_API_KEY

    if not key or key == "your_groq_api_key_here":
        return jsonify({
            "success": False,
            "message": "No Groq API key. Get one free at console.groq.com"
        }), 400

    try:
        mvs = ask_groq(instruction, key)
    except Exception as e:
        return jsonify({"success": False, "message": "Groq API error: " + str(e)})

    ok, msg, code = build_and_run(mvs)

    return jsonify({
        "success":            ok,
        "instruction":        instruction,
        "movements_executed": mvs,
        "generated_code":     code,
        "mode":               "simulation" if SIMULATION_MODE else "hardware",
        "message":            msg
    })

@app.route("/save_command", methods=["POST"])
def save_command():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data"}), 400
    name          = data.get("name", "").strip() or data.get("command", "").strip()
    movements_list = data.get("movements", [])
    if not name:
        return jsonify({"success": False, "message": "Missing command name"}), 400

    ok, msg, code = build_and_run(movements_list if movements_list else ["home"])

    safe         = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    fname        = f"saved_{safe}.py"
    script_path  = os.path.join(SCRIPT_PATH, fname)

    try:
        with open(script_path, "w") as f:
            f.write(code)
        conn = sqlite3.connect(DB)
        cur  = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS actions(command TEXT, action_function TEXT, description TEXT)"
        )
        cur.execute(
            "INSERT OR REPLACE INTO actions VALUES(?,?,?)",
            (name, fname, f"Saved: {name}")
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Saved as '{name}'"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---------------------------
# Entry point
# ---------------------------
if __name__ == "__main__":
    mode = "SIMULATION" if SIMULATION_MODE else "HARDWARE"
    print(f"\n🤖 Robot API running — {len(MOVEMENTS)} movements loaded — mode: {mode}")
    print(f"   Movements file: {MOVEMENTS_FILE}")
    print(f"   Open http://localhost:5000 in your browser\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
