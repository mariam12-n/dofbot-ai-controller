import sqlite3, json, os

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DB             = os.path.join(BASE_DIR, "robot_actions.db")
MOVEMENTS_FILE = os.path.join(BASE_DIR, "movements.json")
GENERATED_DIR  = os.path.join(BASE_DIR, "generated_scripts")

def setup():
    print("\nDofbot AI Controller - Setup\n")
    os.makedirs(GENERATED_DIR, exist_ok=True)
    print("Generated scripts folder ready")
    if not os.path.exists(MOVEMENTS_FILE):
        print("movements.json not found!")
        return
    with open(MOVEMENTS_FILE) as f:
        movements = json.load(f)
    print(f"Loaded {len(movements)} movements")
    conn = sqlite3.connect(DB)
    cur  = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS actions (command TEXT PRIMARY KEY, action_function TEXT, description TEXT)")
    for cmd in ["home","yes","no","celebrate","look left","look right","pick up"]:
        if cmd in movements:
            cur.execute("INSERT OR IGNORE INTO actions VALUES (?,?,?)", (cmd, f"default_{cmd.replace(' ','_')}.py", movements[cmd]["description"]))
    conn.commit()
    conn.close()
    print("Database ready")
    print("\nSetup complete! Run: python3 robot_controller_api.py\n")

if __name__ == "__main__":
    setup()
