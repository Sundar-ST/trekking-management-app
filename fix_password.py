"""
One-time script to fix the admin password stored before hashing was added.
Run this ONCE, then you can delete this file.

Usage:
    python fix_admin_password.py
"""

import sqlite3
from werkzeug.security import generate_password_hash

DB = 'trekking.db'

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check current admin row
admin = cur.execute('SELECT * FROM admin WHERE username = ?', ('admin',)).fetchone()

if admin is None:
    print("No admin account found — nothing to fix.")
else:
    # Re-hash the known plaintext password and update just this row
    new_hash = generate_password_hash('admin123')
    cur.execute(
        'UPDATE admin SET password = ? WHERE username = ?',
        (new_hash, 'admin')
    )
    conn.commit()
    print("Admin password re-hashed successfully.")
    print("You can now log in with username 'admin' and password 'admin123' as before.")

def is_already_hashed(value):
    """
    Werkzeug hashes always start with the method name followed by a colon,
    e.g. 'pbkdf2:sha256:600000$...'. A plaintext password created by a human
    (like 'admin123' or 'mypassword') will essentially never happen to start
    with this exact pattern, so we use it to tell hashed values apart from
    plaintext ones still sitting in the database.
    """
    return value.startswith('pbkdf2:')


# --- Fix staff passwords ---
staff_rows = cur.execute('SELECT staff_id, password FROM staff').fetchall()
staff_fixed = 0
for row in staff_rows:
    if not is_already_hashed(row['password']):
        new_hash = generate_password_hash(row['password'])
        cur.execute(
            'UPDATE staff SET password = ? WHERE staff_id = ?',
            (new_hash, row['staff_id'])
        )
        staff_fixed += 1

# --- Fix user passwords ---
user_rows = cur.execute('SELECT user_id, password FROM user').fetchall()
user_fixed = 0
for row in user_rows:
    if not is_already_hashed(row['password']):
        new_hash = generate_password_hash(row['password'])
        cur.execute(
            'UPDATE user SET password = ? WHERE user_id = ?',
            (new_hash, row['user_id'])
        )
        user_fixed += 1

conn.commit()
print(f"Fixed {staff_fixed} staff account(s) and {user_fixed} user account(s).")
print("Their existing passwords still work exactly as before — just hashed now.")

conn.close()