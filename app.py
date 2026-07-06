from copy import error
from flask import Flask, render_template, request, redirect, url_for, session
from models import get_db_connection, init_db
import sqlite3

app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-later'

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        role=request.form['role']
        email=request.form['email']
        password=request.form['password']

        conn=get_db_connection()

        if role=='admin':
            account=conn.execute(
                'select * from admin where username=? and password=?',
                (email,password,)
            ).fetchone()
        elif role=='staff':
            account=conn.execute(
                'select * from staff where email=? and password=?',
                (email,password)
            ).fetchone()
        elif role=='user':
            account=conn.execute(
                'select * from user where email =? and password=?',
                (email,password)
            ).fetchone()

        conn.close()

        if account is None:
            return render_template('login.html', error='Invalid credentials')

        if role=='staff' and account['status']=='Pending':
            return render_template('login.html',error='Your account is not yet approved by admin')

        if role=='staff' and account['status']=='Blacklisted':
            return render_template('login.html',error='Your account has been blacklisted')

        if role == 'user' and account['status'] == 'Blacklisted':
            return render_template('login.html', error='Your account has been blacklisted')

        session['role']=role
        session['id']=account[f'{role}_id']
        session['name']=account['username'] if role =='admin' else account['name']

        return redirect(url_for(f'{role}_dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role')!='admin':
        return redirect(url_for('login'))
    #return f"Welcome Admin {session['name']}! (dashboard coming next)"
    
    search = request.args.get('search', '')

    conn=get_db_connection()

    #stats for top of dashboard
    trek_count=conn.execute('select count(*) from trek').fetchone()[0]
    user_count=conn.execute('select count(*) from user').fetchone()[0]
    staff_count=conn.execute('select count(*) from staff').fetchone()[0]
    booking_count=conn.execute('select count(*) from booking').fetchone()[0]
    
    if search:
        all_staff = conn.execute(
            "SELECT * FROM staff WHERE name LIKE ? OR email LIKE ? ",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        all_staff=conn.execute('select * from staff').fetchall()

    conn.close()

    return render_template('admin_dashboard.html',
        trek_count=trek_count,
        user_count=user_count,
        staff_count=staff_count,
        booking_count=booking_count,
        all_staff=all_staff,
        search=search
    )


@app.route('/admin/staff/<int:staff_id>/approve',methods=['POST'])
def approve_staff(staff_id):
    if session.get('role')!='admin':
        return redirect(url_for('login'))

    conn=get_db_connection()
    conn.execute("update staff set status='Approved' where staff_id=?",(staff_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/staff/<int:staff_id>/blacklist',methods=["POST"])
def blacklist_staff(staff_id):
    if session.get('role')!='admin':
        return redirect(url_for('login'))

    conn=get_db_connection()
    conn.execute("update staff set status='Blacklisted' where staff_id=?",(staff_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))
    

@app.route('/admin/treks')
def manage_treks():
    if session.get('role')!='admin':
        return redirect(url_for('login'))

    search = request.args.get('search','')

    conn=get_db_connection()

    if search:
        treks=conn.execute(
            "select * from trek where name like ? or location like ?",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        treks=conn.execute("select * from trek").fetchall()

    conn.close()

    return render_template('manage_treks.html',treks=treks, search=search)

@app.route('/admin/treks/add', methods=['GET','POST'])
def add_trek():
    if session.get('role')!='admin':
        return redirect(url_for('login'))

    if request.method=='POST':
        name=request.form['name']
        location=request.form['location']
        difficulty=request.form['difficulty']
        duration_days=request.form['duration_days']
        available_slots=request.form['available_slots']
        start_date=request.form['start_date']
        end_date=request.form['end_date']

        conn=get_db_connection()
        conn.execute('''
            insert into trek (name,location,difficulty,duration_days,available_slots,status,start_date,end_date)
            values (?,?,?,?,?,?,?,?)''',
            (name,location,difficulty,duration_days,available_slots,'Pending',start_date,end_date))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_treks'))

    return render_template('add_trek.html')


@app.route('/admin/treks/<int:trek_id>/assign', methods=['GET', 'POST'])
def assign_staff(trek_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        staff_id = request.form['staff_id']
        status = request.form['status']

        conn.execute(
            'UPDATE trek SET assigned_staff_id = ?, status = ? WHERE trek_id = ?',
            (staff_id, status, trek_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('manage_treks'))

    trek = conn.execute('SELECT * FROM trek WHERE trek_id = ?', (trek_id,)).fetchone()
    approved_staff = conn.execute(
        "SELECT * FROM staff WHERE status = 'Approved'"
    ).fetchall()
    conn.close()

    return render_template('assign_staff.html', trek=trek, approved_staff=approved_staff)


@app.route('/admin/users')
def manage_users():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    search = request.args.get('search', '')

    conn = get_db_connection()

    if search:
        all_users = conn.execute(
            "SELECT * FROM user WHERE name LIKE ? OR email LIKE ?",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        all_users = conn.execute('SELECT * FROM user').fetchall()

    conn.close()

    return render_template('manage_users.html', all_users=all_users, search=search)





@app.route('/admin/users/<int:user_id>/blacklist', methods=['POST'])
def blacklist_user(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("UPDATE user SET status = 'Blacklisted' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('manage_users'))


@app.route('/admin/users/<int:user_id>/activate', methods=['POST'])
def activate_user(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("UPDATE user SET status = 'Active' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('manage_users'))


@app.route('/staff/dashboard')
def staff_dashboard():
    if session.get('role') != 'staff':
        return redirect(url_for('login'))
    return f"Welcome {session['name']}! (staff dashboard coming next)"


@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role')!='user':
        return redirect(url_for('login'))
    return f"welcome {session['name']}! (user dashboard coming next)"


@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        role=request.form['role']
        name=request.form['name']
        email=request.form['email']
        password=request.form['password']
        contact=request.form['contact']

        conn=get_db_connection()

        try:
            if role=='staff':
                conn.execute(
                    'insert into staff(name,email,password,contact,status) values(?,?,?,?,?)',
                    (name,email,password,contact,'Pending')
                )
            elif role=='user':
                conn.execute(
                    'insert into user(name,email,password,contact,status) values(?,?,?,?,?)',
                    (name,email,password,contact,'Active')
                )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html',error='Email already exists')

        conn.close()

        if role=='staff':
            return render_template('login.html', error='Staff registration pending for approval')
        elif role == 'user':
            return render_template('login.html', error='User registration successful')
        return render_template('login.html')
    
    return render_template('register.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)