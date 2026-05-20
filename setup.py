"""
setup.py
--------
Run this once before starting the robot API for the first time.
Creates the SQLite database with default commands.

Usage:
    python3 setup.py
"""

import sqlite3, json, os

SCRIPT_PATH    = "/home/nadeem/dofbot-Pi/10.Basic control course"
DB             = "/home/nadeem/robot_actions.db"
MOVEMENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "movements.json")
GENERATED_DIR  = "/home/nadeem/generated_scripts"

def setup():
    print("\n🤖 Dofbot AI Controller — Setup\n")
    os.makedirs(GENERATED_DIR, exist_ok=True)
    print(f"✓ Generated scripts folder ready")

    if not os.path.exists(MOVEMENTS_FILE):
        print(f"✗ movements.json not found!")
        return

    with open(MOVEMENTS_FILE) as f:
        movements = json.load(f)
    print(f"✓ Loaded {len(movements)} movements")

    conn = sqlite3.connect(DB)
    cur  = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS actions (command TEXT PRIMARY KEY, action_function TEXT, description TEXT)")

    for cmd in ["home","yes","no","celebrate","look left","look right","pick up"]:
        if cmd in movements:
            cur.execute("INSERT OR IGNORE INTO actions VALUES (?,?,?)", (cmd, f"default_{cmd.replace(' ','_')}.py", movements[cmd]["description"]))

    conn.commit()
    conn.close()
    print(f"✓ Database ready")
    print("\n✅ Setup complete! Run: python3 robot_controller_api.py\n")

if __name__ == "__main__":
    setup()
