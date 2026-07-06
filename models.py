import sqlite3
from werkzeug.security import generate_password_hash

DB = 'trekking.db'

def get_db_connection():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init_db():
    conn=get_db_connection()
    cur=conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin(
            admin_id integer primary key autoincrement,
            username text unique not null,
            password text not null)
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS staff(
            staff_id integer primary key autoincrement,
            name text not null,
            email text unique not null,
            password text not null,
            contact text,
            status text not null default 'Pending'
            -- status: Pending / Approved / Blacklisted
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user(
            user_id integer primary key autoincrement,
            name text not null,
            email text unique not null,
            password text not null,
            contact integer,
            status text not null default 'Active',
            -- status: Active / Blacklisted
            CHECK (contact >= 1000000000 AND contact <= 9999999999)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS trek(
            trek_id integer primary key autoincrement,
            name text not null,
            location text not null,
            difficulty text not null,
            duration_days integer not null,
            available_slots integer not null,
            assigned_staff_id integer,
            status text not null default 'Pending',
            -- status: Pending/Approved/Open/Closed/Completed
            start_date text,
            end_date text,
            foreign key (assigned_staff_id) references staff(staff_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS booking(
            booking_id integer primary key autoincrement,
            user_id integer not null,
            trek_id integer not null,
            booking_date text not null,
            status text not null default 'Booked',
            --status: Booked/Cancelled/Completed
            FOREIGN KEY(user_id) references user(user_id),
            FOREIGN KEY (trek_id) references trek(trek_id)
            )
        ''')

    cur.execute('SELECT * FROM admin where username =?',('admin',))
    if cur.fetchone() is None:
        cur.execute(
            'INSERT INTO admin(username,password) values (?,?)',
            ('admin',generate_password_hash('admin123'))
        )

    conn.commit()
    conn.close()
    print("Database initialised successfully.")


if __name__=='__main__':
    init_db()