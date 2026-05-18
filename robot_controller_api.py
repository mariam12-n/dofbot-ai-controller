"""
robot_controller_api.py
Smart Flask API for Yahboom Dofbot-Pi robot arm.
Endpoints:
  GET  /status     -> API status
  GET  /commands   -> list DB commands
  GET  /movements  -> list all library movements
  POST /run        -> run a DB command by name
  POST /move       -> run a library movement by name
  POST /ai         -> Groq chains library movements
"""
import sys, os, sqlite3, requests, json
from flask import Flask, request, jsonify

SCRIPT_PATH = "/home/nadeem/dofbot-Pi/10.Basic control course"
DB = "/home/nadeem/robot_actions.db"
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
GENERATED_DIR = "/home/nadeem/generated_scripts"
SPEED = 3000

if SCRIPT_PATH not in sys.path:
    sys.path.insert(0, SCRIPT_PATH)
os.makedirs(GENERATED_DIR, exist_ok=True)

app = Flask(__name__)

MOVEMENTS = {
    "home":         {"description":"Return to home","steps":[[90,90,90,90,90,180,SPEED,2]]},
    "look down":    {"description":"Look down","steps":[[90,90,90,90,90,180,SPEED,1],[89,74,22,42,89,174,SPEED,2],[90,90,90,90,90,180,SPEED,1]]},
    "look left":    {"description":"Look left","steps":[[90,90,90,90,90,180,SPEED,1],[0,81,55,37,89,174,SPEED,2],[90,90,90,90,90,180,SPEED,1]]},
    "look right":   {"description":"Look right","steps":[[90,90,90,90,90,180,SPEED,1],[177,83,7,90,89,175,SPEED,2],[90,90,90,90,90,180,SPEED,1]]},
    "look up":      {"description":"Look up","steps":[[90,90,90,90,90,180,SPEED,1],[90,50,90,90,90,180,SPEED,2],[90,90,90,90,90,180,SPEED,1]]},
    "point left":   {"description":"Point left","steps":[[90,90,90,90,90,180,SPEED,1],[12,31,62,90,89,173,SPEED,3],[90,90,90,90,90,180,SPEED,1]]},
    "point right":  {"description":"Point right","steps":[[90,90,90,90,90,180,SPEED,1],[169,18,74,90,89,174,SPEED,3],[90,90,90,90,90,180,SPEED,1]]},
    "infront":      {"description":"Scan in front","steps":[[90,90,90,90,90,180,SPEED,1],[90,70,13,83,89,175,SPEED,2],[0,65,13,70,89,175,SPEED,3],[180,65,13,100,89,175,SPEED,3],[90,90,90,90,90,180,SPEED,1]]},
    "pick up":      {"description":"Pick up object - stays holding","steps":[[90,90,90,90,90,0,SPEED,1],[89,55,20,40,89,0,SPEED,2],[89,55,20,40,89,180,1000,2],[90,90,90,90,90,180,SPEED,2]]},
    "pick up left": {"description":"Pick up from left","steps":[[90,90,90,90,90,180,SPEED,1],[0,90,90,90,90,180,SPEED,2],[0,90,90,90,90,0,SPEED,1],[0,55,20,40,89,0,SPEED,2],[0,55,20,40,89,180,1000,2],[0,90,90,90,90,180,SPEED,2],[90,90,90,90,90,180,SPEED,1]]},
    "pick up right":{"description":"Pick up from right","steps":[[90,90,90,90,90,180,SPEED,1],[177,90,90,90,90,180,SPEED,2],[177,90,90,90,90,0,SPEED,2],[177,55,20,40,89,0,SPEED,3],[177,55,20,40,89,180,1000,3],[177,90,90,90,90,180,SPEED,2],[90,90,90,90,90,180,SPEED,1]]},
    "put left":     {"description":"Place on left","steps":[[0,55,20,40,89,180,SPEED,2],[0,55,20,40,89,0,SPEED,2],[90,90,90,90,90,0,SPEED,1],[90,90,90,90,90,180,SPEED,1]]},
    "put right":    {"description":"Place on right","steps":[[177,55,20,40,89,180,SPEED,2],[177,55,20,40,89,0,SPEED,2],[90,90,90,90,90,0,SPEED,1],[90,90,90,90,90,180,SPEED,1]]},
    "put front":    {"description":"Place in front","steps":[[89,55,20,40,89,180,SPEED,2],[89,55,20,40,89,0,SPEED,2],[90,90,90,90,90,0,SPEED,1],[90,90,90,90,90,180,SPEED,1]]},
    "celebrate":    {"description":"Celebrate","steps":[[90,90,90,90,90,180,SPEED,1],[90,60,60,90,90,0,SPEED,2],[90,60,60,90,90,180,500,0.2],[90,60,60,90,90,0,500,0.2],[90,60,60,90,90,180,500,0.2],[90,60,60,90,90,0,500,0.2],[90,60,60,90,90,180,500,0.2],[90,90,90,90,90,180,SPEED,1]]},
    "no":           {"description":"Shake no","steps":[[90,90,90,90,90,180,SPEED,1],[89,60,49,75,89,173,SPEED,1],[60,60,49,75,89,173,1500,0.4],[120,60,49,75,89,173,1500,0.4],[60,60,49,75,89,173,1500,0.4],[120,60,49,75,89,173,1500,0.4],[90,90,90,90,90,180,SPEED,1]]},
    "yes":          {"description":"Nod yes","steps":[[90,90,90,90,90,180,SPEED,1],[89,60,49,75,89,173,SPEED,1],[89,45,49,75,89,173,1500,0.4],[89,75,49,75,89,173,1500,0.4],[89,45,49,75,89,173,1500,0.4],[89,75,49,75,89,173,1500,0.4],[90,90,90,90,90,180,SPEED,1]]},
}

def build_and_run(movements_list):
    all_steps = []
    holding = False
    for name in movements_list:
        if name not in MOVEMENTS:
            continue
        steps = MOVEMENTS[name]["steps"]
        if name == "home" and holding:
            steps = [[s[0],s[1],s[2],s[3],s[4],180,s[6],s[7]] for s in steps]
        all_steps.extend(steps)
        if "pick up" in name:
            holding = True
        if "put" in name:
            holding = False

    lines = [
        "import time,sys",
        "sys.path.append('/home/nadeem/dofbot-Pi/10.Basic control course')",
        "from Arm_Lib import Arm_Device",
        "Arm=Arm_Device()",
        "try:",
        "    Arm.Arm_serial_set_torque(True)",
    ]
    for s in all_steps:
        lines.append(f"    Arm.Arm_serial_servo_write6({s[0]},{s[1]},{s[2]},{s[3]},{s[4]},{s[5]},{s[6]})")
        lines.append(f"    time.sleep({s[7]})")
    lines += ["finally:","    pass  # keep torque ON so gripper holds object"]

    code = "\n".join(lines)
    path = os.path.join(GENERATED_DIR, "gen_latest.py")
    with open(path,"w") as f: f.write(code)
    exit_code = os.system(f"cd '{SCRIPT_PATH}' && python3 '{path}'")
    return exit_code == 0, code

def get_commands():
    try:
        conn=sqlite3.connect(DB); cur=conn.cursor()
        cur.execute("SELECT command,action_function,description FROM actions")
        rows=cur.fetchall(); conn.close(); return rows
    except: return []

def run_saved(command):
    try:
        conn=sqlite3.connect(DB); cur=conn.cursor()
        cur.execute("SELECT action_function FROM actions WHERE command=?",(command,))
        row=cur.fetchone(); conn.close()
    except Exception as e: return False,"DB error: "+str(e)
    if not row: return False,"Command not found: "+command
    path=os.path.join(SCRIPT_PATH,row[0])
    if not os.path.exists(path): return False,"Script not found: "+path
    exit_code=os.system(f"cd '{SCRIPT_PATH}' && python3 '{path}'")
    return exit_code==0, "Done" if exit_code==0 else "Failed"

def ask_groq(instruction,key):
    mv_list="\n".join(f'- "{n}": {m["description"]}' for n,m in MOVEMENTS.items())
    prompt=f"""You control a robot arm. Pick movements from this list and return ONLY a JSON array.
MOVEMENTS:\n{mv_list}
RULES:
- Return ONLY a JSON array like ["pick up","home"]
- NEVER add "home" after pick up movements — arm stays holding
- Only release with put left/right/front when user says put/place/drop
- For look/celebrate/yes/no: end with "home"
- Return ONLY the JSON array, nothing else

User: {instruction}

IMPORTANT EXAMPLES:
- "pick up from front" -> ["pick up"]
- "pick up and put left" -> ["pick up","put left"]
- "pick up and put right" -> ["pick up","put right"]
- "look left then right" -> ["look left","look right","home"]
- "say yes" -> ["yes","home"]
- "celebrate" -> ["celebrate","home"]
- "drop it" -> ["put front"]
- NEVER add movements that user did not ask for
- NEVER add "look left" or "look right" unless user specifically says look"""
    r=requests.post(GROQ_URL,
        json={"model":GROQ_MODEL,"messages":[{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":200},
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},timeout=30)
    r.raise_for_status()
    raw=r.json()["choices"][0]["message"]["content"].strip()
    if "```" in raw: raw="\n".join(l for l in raw.split("\n") if not l.strip().startswith("```"))
    return json.loads(raw.strip())

@app.route("/")
def index():
    ui=os.path.join(os.path.dirname(os.path.abspath(__file__)),"robot_web_ui.html")
    if os.path.exists(ui):
        with open(ui) as f: return f.read(),200,{"Content-Type":"text/html"}
    return jsonify({"status":"running"})

@app.route("/status")
def status():
    return jsonify({"status":"online","commands_loaded":len(get_commands()),"movements_loaded":len(MOVEMENTS)})

@app.route("/commands")
def commands():
    rows=get_commands()
    return jsonify({"commands":[{"command":r[0],"function":r[1],"description":r[2]} for r in rows]})

@app.route("/movements")
def movements():
    return jsonify({"movements":[{"name":n,"description":m["description"],"steps":len(m["steps"])} for n,m in MOVEMENTS.items()]})

@app.route("/run",methods=["POST"])
def run():
    data=request.get_json()
    if not data or "command" not in data: return jsonify({"success":False,"message":"Missing command"}),400
    ok,msg=run_saved(data["command"].strip())
    return jsonify({"success":ok,"message":msg})

@app.route("/move",methods=["POST"])
def move():
    data=request.get_json()
    if not data or "movement" not in data: return jsonify({"success":False,"message":"Missing movement"}),400
    ok,code=build_and_run([data["movement"].strip()])
    return jsonify({"success":ok,"movement":data["movement"]})

@app.route("/ai",methods=["POST"])
def ai():
    data=request.get_json()
    if not data or "instruction" not in data: return jsonify({"success":False,"message":"Missing instruction"}),400
    instruction=data["instruction"].strip()
    key=data.get("groq_key","").strip() or GROQ_API_KEY
    try:
        mvs=ask_groq(instruction,key)
    except Exception as e:
        return jsonify({"success":False,"message":"Groq error: "+str(e)})
    ok,code=build_and_run(mvs)
    return jsonify({"success":ok,"instruction":instruction,"movements_executed":mvs,"generated_code":code,"message":"Done!" if ok else "Failed"})

@app.route("/save_command",methods=["POST"])
def save_command():
    data=request.get_json()
    if not data: return jsonify({"success":False,"message":"No data"}),400
    name=data.get("name","").strip()
    code=data.get("code","").strip()
    if not name or not code: return jsonify({"success":False,"message":"Missing name or code"}),400
    safe="".join(c if c.isalnum() or c=="_" else "_" for c in name)
    fname=f"saved_{safe}.py"
    path=os.path.join(SCRIPT_PATH,fname)
    with open(path,"w") as f: f.write(code)
    try:
        conn=sqlite3.connect(DB); cur=conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS actions(command TEXT,action_function TEXT,description TEXT)")
        cur.execute("INSERT INTO actions VALUES(?,?,?)",(name,fname,f"Saved: {name}"))
        conn.commit(); conn.close()
    except Exception as e: return jsonify({"success":False,"message":str(e)})
    return jsonify({"success":True,"message":f"Saved as {fname}"})

if __name__=="__main__":
    print(f"\nRobot API running — {len(MOVEMENTS)} movements loaded")
    app.run(host="0.0.0.0",port=5000,debug=False)
