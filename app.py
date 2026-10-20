from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import os, sqlite3
from datetime import datetime, timezone, timedelta
from werkzeug.utils import secure_filename
from functools import wraps
try:
    import psycopg
    from psycopg.rows import dict_row
    HAS_POSTGRES = True
    USE_PSYCOPG3 = True
except:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        HAS_POSTGRES = True
        USE_PSYCOPG3 = False
    except:
        HAS_POSTGRES = False
        USE_PSYCOPG3 = False

app = Flask(__name__)
app.secret_key = 'zdspgc2026'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

PH_TZ = timezone(timedelta(hours=8))

def get_ph_now():
    return datetime.now(PH_TZ)

def get_db():
    db_url = os.environ.get('DATABASE_URL')
    if HAS_POSTGRES and db_url:
        try:
            if not hasattr(g, '_database') or g._database is None:
                url = db_url
                if url.startswith("postgres://"):
                    url = url.replace("postgres://", "postgresql://", 1)
                clean_url = url.split("?")[0]
                if USE_PSYCOPG3:
                    g._database = psycopg.connect(clean_url, row_factory=dict_row, connect_timeout=10)
                else:
                    g._database = psycopg2.connect(clean_url, sslmode='require', cursor_factory=RealDictCursor, connect_timeout=10)
                g.db_is_pg = True
                return g._database
            else:
                return g._database
        except Exception as e:
            print(f"PG CONNECT FAILED: {e}")
            g.db_is_pg = False
    g.db_is_pg = False
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def is_pg():
    return getattr(g, 'db_is_pg', False)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        try:
            db.close()
        except:
            pass

def init_db():
    db = get_db()
    pg = is_pg()
    print(f"INIT DB - is_pg: {pg}")
    if pg:
        cur = db.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, name TEXT, is_approved INTEGER DEFAULT 1, username TEXT UNIQUE)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS items (id SERIAL PRIMARY KEY, name TEXT, category TEXT, description TEXT, location TEXT, status TEXT, image TEXT, reported_by TEXT, date_reported TEXT, date_returned TEXT, time_returned TEXT, claimed_by TEXT)''')
        cur.execute("SELECT COUNT(*) as c FROM users")
        row = cur.fetchone()
        count = row['c'] if isinstance(row, dict) else row[0]
        if count==0:
            cur.execute("INSERT INTO users (email,password,role,name,is_approved,username) VALUES (%s,%s,%s,%s,%s,%s)", ('admin@zdspgc.edu.ph','admin123','admin','Admin',1,'admin'))
        cur.execute("SELECT COUNT(*) as c FROM items")
        row = cur.fetchone()
        count = row['c'] if isinstance(row, dict) else row[0]
        if count==0:
            now = get_ph_now().strftime("%Y-%m-%d %I:%M:%S %p")
            cur.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", ('Brown Leather Wallet','Wallet','Found near library with cash inside','Library - 2nd Floor','Found','wallet.jpg','admin@zdspgc.edu.ph',now))
            cur.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", ('Student ID Card - Juan Dela Cruz','ID Card','ID with blue lanyard','Cafeteria','Matched','id.jpg','admin@zdspgc.edu.ph',now))
            cur.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", ('Set of Keys with Keychain','Keys','3 keys + black keychain','Parking Lot','Lost','keys.jpg','admin@zdspgc.edu.ph',now))
            cur.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", ('Black Backpack Jansport','Bag','Returned to owner','Admin Office','Returned','backpack.jpg','admin@zdspgc.edu.ph',now))
        db.commit()
    else:
        db.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT, name TEXT, is_approved INTEGER DEFAULT 1, username TEXT UNIQUE)''')
        try:
            db.execute("ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 1")
        except:
            pass
        try:
            db.execute("ALTER TABLE users ADD COLUMN username TEXT")
        except:
            pass
        db.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, category TEXT, description TEXT, location TEXT, status TEXT, image TEXT, reported_by TEXT, date_reported TEXT, date_returned TEXT, time_returned TEXT, claimed_by TEXT)''')
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]==0:
            db.execute("INSERT INTO users (email,password,role,name,is_approved,username) VALUES (?,?,?,?,?,?)", ('admin@zdspgc.edu.ph','admin123','admin','Admin',1,'admin'))
        if db.execute("SELECT COUNT(*) FROM items").fetchone()[0]==0:
            now = get_ph_now().strftime("%Y-%m-%d %I:%M:%S %p")
            db.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (?,?,?,?,?,?,?,?)", ('Brown Leather Wallet','Wallet','Found near library with cash inside','Library - 2nd Floor','Found','wallet.jpg','admin@zdspgc.edu.ph',now))
            db.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (?,?,?,?,?,?,?,?)", ('Student ID Card - Juan Dela Cruz','ID Card','ID with blue lanyard','Cafeteria','Matched','id.jpg','admin@zdspgc.edu.ph',now))
            db.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (?,?,?,?,?,?,?,?)", ('Set of Keys with Keychain','Keys','3 keys + black keychain','Parking Lot','Lost','keys.jpg','admin@zdspgc.edu.ph',now))
            db.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (?,?,?,?,?,?,?,?)", ('Black Backpack Jansport','Bag','Returned to owner','Admin Office','Returned','backpack.jpg','admin@zdspgc.edu.ph',now))
        db.commit()
        db.close()

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*a,**kw)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if session.get('role')!='admin':
            flash('Pang Admin lang ito!')
            return redirect('/')
        return f(*a,**kw)
    return dec

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email']
        pw=request.form['password']
        try:
            db=get_db()
            if is_pg():
                cur=db.cursor()
                cur.execute("SELECT * FROM users WHERE (email=%s OR username=%s) AND password=%s",(email,email,pw))
                user=cur.fetchone()
            else:
                user=db.execute("SELECT * FROM users WHERE (email=? OR username=?) AND password=?",(email,email,pw)).fetchone()
                db.close()
            if user:
                if user['is_approved']==0:
                    flash('Hindi pa approved account mo, hintay lang sa admin.')
                    return render_template('login.html')
                session['user_id']=user['id']
                session['email']=user['email']
                session['role']=user['role']
                session['name']=user['name']
                return redirect('/')
            flash('Mali email o password')
        except Exception as e:
            print(f"LOGIN ERROR: {e}")
            flash(f'Problema sa database, pakisubukan ulit: {e}')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username'].strip()
        name=request.form['name'].strip()
        pw=request.form['password']
        role=request.form['role']
        email=request.form['email'].strip()
        if not email:
            flash('Kailangan ng email! Ilagay mo email mo.')
            return render_template('register.html')
        if role not in ['staff','student']:
            flash('Bawal role na yan, staff o student lang pwede.')
            return render_template('register.html')
        db=get_db()
        try:
            is_approved = 1 if role=='student' else 0
            if is_pg():
                cur=db.cursor()
                cur.execute("INSERT INTO users (username,email,password,role,name,is_approved) VALUES (%s,%s,%s,%s,%s,%s)", (username,email,pw,role,name,is_approved))
                db.commit()
            else:
                db.execute("INSERT INTO users (username,email,password,role,name,is_approved) VALUES (?,?,?,?,?,?)", (username,email,pw,role,name,is_approved))
                db.commit()
                db.close()
            if role=='student':
                flash('Tagumpay! Auto-approved ka na, pwede ka na mag login.')
            else:
                flash('Tagumpay! Hintayin mo approval ni admin.')
            return redirect('/login')
        except Exception as e:
            if not is_pg():
                db.close()
            print(e)
            flash('Umuulit username o email!')
            return render_template('register.html')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
@login_required
def dashboard():
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("SELECT COUNT(*) as c FROM items WHERE status='Lost'")
        lost=cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM items WHERE status='Found'")
        found=cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM items WHERE status='Matched'")
        matched=cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM items WHERE status='Returned'")
        returned=cur.fetchone()['c']
        cur.execute("SELECT * FROM items ORDER BY id DESC LIMIT 8")
        items=cur.fetchall()
    else:
        lost=db.execute("SELECT COUNT(*) FROM items WHERE status='Lost'").fetchone()[0]
        found=db.execute("SELECT COUNT(*) FROM items WHERE status='Found'").fetchone()[0]
        matched=db.execute("SELECT COUNT(*) FROM items WHERE status='Matched'").fetchone()[0]
        returned=db.execute("SELECT COUNT(*) FROM items WHERE status='Returned'").fetchone()[0]
        items=db.execute("SELECT * FROM items ORDER BY id DESC LIMIT 8").fetchall()
        db.close()
    return render_template('dashboard.html', lost=lost, found=found, matched=matched, returned=returned, items=items)

@app.route('/items')
@login_required
def items_page():
    db=get_db()
    status=request.args.get('status','All')
    q=request.args.get('q','').strip()
    if is_pg():
        cur=db.cursor()
        if q:
            like=f"%{q}%"
            if status=='All':
                cur.execute("SELECT * FROM items WHERE name ILIKE %s OR category ILIKE %s OR location ILIKE %s OR description ILIKE %s OR reported_by ILIKE %s ORDER BY id DESC",(like,like,like,like,like))
            else:
                cur.execute("SELECT * FROM items WHERE status=%s AND (name ILIKE %s OR category ILIKE %s OR location ILIKE %s OR description ILIKE %s OR reported_by ILIKE %s) ORDER BY id DESC",(status,like,like,like,like,like))
        else:
            if status=='All':
                cur.execute("SELECT * FROM items ORDER BY id DESC")
            else:
                cur.execute("SELECT * FROM items WHERE status=%s ORDER BY id DESC",(status,))
        items=cur.fetchall()
    else:
        if q:
            like=f"%{q}%"
            if status=='All':
                items=db.execute("SELECT * FROM items WHERE name LIKE? OR category LIKE? OR location LIKE? OR description LIKE? OR reported_by LIKE? ORDER BY id DESC",(like,like,like,like,like)).fetchall()
            else:
                items=db.execute("SELECT * FROM items WHERE status=? AND (name LIKE? OR category LIKE? OR location LIKE? OR description LIKE? OR reported_by LIKE?) ORDER BY id DESC",(status,like,like,like,like,like)).fetchall()
        else:
            if status=='All':
                items=db.execute("SELECT * FROM items ORDER BY id DESC").fetchall()
            else:
                items=db.execute("SELECT * FROM items WHERE status=? ORDER BY id DESC",(status,)).fetchall()
        db.close()
    return render_template('items.html', items=items, filter=status, q=q)

@app.route('/report', methods=['GET','POST'])
@login_required
def report():
    if request.method=='POST':
        name=request.form['name']
        category=request.form['category']
        desc=request.form['description']
        loc=request.form['location']
        stat=request.form['status']
        file=request.files.get('image')
        filename='no-image.png'
        if file and file.filename!='':
            filename=secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        now=get_ph_now().strftime("%Y-%m-%d %I:%M:%S %p")
        db=get_db()
        if is_pg():
            cur=db.cursor()
            cur.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (name,category,desc,loc,stat,filename,session['email'],now))
            db.commit()
        else:
            db.execute("INSERT INTO items (name,category,description,location,status,image,reported_by,date_reported) VALUES (?,?,?,?,?,?,?,?)", (name,category,desc,loc,stat,filename,session['email'],now))
            db.commit()
            db.close()
        return redirect('/items')
    return render_template('report.html')

@app.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_item(id):
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("SELECT * FROM items WHERE id=%s",(id,))
        item=cur.fetchone()
    else:
        item=db.execute("SELECT * FROM items WHERE id=?",(id,)).fetchone()
    if session.get('role') not in ['admin','staff'] and item['reported_by']!=session.get('email'):
        if not is_pg():
            db.close()
        flash('Ikaw lang nag report, staff o admin lang pwede mag edit')
        return redirect('/items')
    if request.method=='POST':
        file=request.files.get('image')
        filename=item['image']
        if file and file.filename!='':
            filename=secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        if is_pg():
            cur.execute("UPDATE items SET name=%s,category=%s,description=%s,location=%s,status=%s,image=%s WHERE id=%s", (request.form['name'],request.form['category'],request.form['description'],request.form['location'],request.form['status'],filename,id))
            db.commit()
        else:
            db.execute("UPDATE items SET name=?,category=?,description=?,location=?,status=?,image=? WHERE id=?", (request.form['name'],request.form['category'],request.form['description'],request.form['location'],request.form['status'],filename,id))
            db.commit()
            db.close()
        return redirect('/items')
    if not is_pg():
        db.close()
    return render_template('edit.html', item=item)

@app.route('/delete/<int:id>')
@login_required
def delete_item(id):
    if session.get('role')!='admin':
        flash('Pang admin lang mag delete')
        return redirect('/items')
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("DELETE FROM items WHERE id=%s",(id,))
        db.commit()
    else:
        db.execute("DELETE FROM items WHERE id=?",(id,))
        db.commit()
        db.close()
    return redirect('/items')

@app.route('/return/<int:id>')
@login_required
def return_item(id):
    if session.get('role')!='admin':
        flash('Pang admin lang mag return!')
        return redirect('/items')
    now=get_ph_now()
    full=now.strftime("%Y-%m-%d %I:%M:%S %p")
    t=now.strftime("%I:%M:%S %p")
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("UPDATE items SET status='Returned', date_returned=%s, time_returned=%s, claimed_by=%s WHERE id=%s", (full,t,session['email'],id))
        db.commit()
    else:
        db.execute("UPDATE items SET status='Returned', date_returned=?, time_returned=?, claimed_by=? WHERE id=?", (full,t,session['email'],id))
        db.commit()
        db.close()
    return redirect('/')

@app.route('/found/<int:id>')
@login_required
def found_item(id):
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("SELECT * FROM items WHERE id=%s",(id,))
        item=cur.fetchone()
        if item and item['status']=='Lost':
            cur.execute("UPDATE items SET status='Found' WHERE id=%s",(id,))
            db.commit()
    else:
        item=db.execute("SELECT * FROM items WHERE id=?",(id,)).fetchone()
        if item and item['status']=='Lost':
            db.execute("UPDATE items SET status='Found' WHERE id=?",(id,))
            db.commit()
        db.close()
    return redirect('/items')

@app.route('/match/<int:id>')
@login_required
def match_item(id):
    if session.get('role') not in ['admin','staff']:
        flash('Staff o Admin lang pwede mag match!')
        return redirect('/matches')
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("UPDATE items SET status='Matched' WHERE id=%s",(id,))
        db.commit()
    else:
        db.execute("UPDATE items SET status='Matched' WHERE id=?",(id,))
        db.commit()
        db.close()
    return redirect('/matches')

@app.route('/details/<int:id>')
@login_required
def details(id):
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("SELECT * FROM items WHERE id=%s",(id,))
        item=cur.fetchone()
    else:
        item=db.execute("SELECT * FROM items WHERE id=?",(id,)).fetchone()
        db.close()
    return render_template('details.html', item=item)

@app.route('/matches')
@login_required
def matches_page():
    if session.get('role') not in ['admin','staff']:
        flash('Staff o Admin lang!')
        return redirect('/')
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("SELECT * FROM items WHERE status='Matched' ORDER BY id DESC")
        matched=cur.fetchall()
    else:
        matched=db.execute("SELECT * FROM items WHERE status='Matched' ORDER BY id DESC").fetchall()
        db.close()
    return render_template('matches.html', matched=matched)

@app.route('/claims')
@login_required
def claims_page():
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("SELECT * FROM items WHERE status='Returned' ORDER BY date_returned DESC")
        items=cur.fetchall()
    else:
        items=db.execute("SELECT * FROM items WHERE status='Returned' ORDER BY date_returned DESC").fetchall()
        db.close()
    return render_template('claims.html', items=items)

@app.route('/users')
@login_required
@admin_required
def users_page():
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("SELECT * FROM users")
        users=cur.fetchall()
        cur.execute("SELECT * FROM users WHERE is_approved=0")
        pending=cur.fetchall()
    else:
        users=db.execute("SELECT * FROM users").fetchall()
        pending=db.execute("SELECT * FROM users WHERE is_approved=0").fetchall()
        db.close()
    return render_template('users.html', users=users, pending=pending)

@app.route('/approve/<int:id>')
@login_required
@admin_required
def approve_user(id):
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("UPDATE users SET is_approved=1 WHERE id=%s",(id,))
        db.commit()
    else:
        db.execute("UPDATE users SET is_approved=1 WHERE id=?",(id,))
        db.commit()
        db.close()
    flash('Na-approve na user!')
    return redirect('/users')

@app.route('/reject/<int:id>')
@login_required
@admin_required
def reject_user(id):
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("DELETE FROM users WHERE id=%s",(id,))
        db.commit()
    else:
        db.execute("DELETE FROM users WHERE id=?",(id,))
        db.commit()
        db.close()
    flash('Na-reject at nabura user.')
    return redirect('/users')

@app.route('/archive')
@login_required
@admin_required
def archive_page():
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("SELECT * FROM items WHERE status='Returned'")
        items=cur.fetchall()
    else:
        items=db.execute("SELECT * FROM items WHERE status='Returned'").fetchall()
        db.close()
    return render_template('archive.html', items=items)

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile_page():
    db=get_db()
    if is_pg():
        cur=db.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s",(session['user_id'],))
        user=cur.fetchone()
    else:
        user=db.execute("SELECT * FROM users WHERE id=?",(session['user_id'],)).fetchone()
    if request.method=='POST':
        name=request.form['name'].strip()
        username=request.form['username'].strip()
        email=request.form['email'].strip()
        pw=request.form['password'].strip()
        if is_pg():
            cur.execute("SELECT * FROM users WHERE (username=%s OR email=%s) AND id!=%s", (username, email, session['user_id']))
            check=cur.fetchone()
        else:
            check=db.execute("SELECT * FROM users WHERE (username=? OR email=?) AND id!=?", (username, email, session['user_id'])).fetchone()
        if check:
            if not is_pg():
                db.close()
            flash('Gamit na username o email!')
            return render_template('profile.html', user=user)
        if pw:
            if is_pg():
                cur.execute("UPDATE users SET name=%s, username=%s, email=%s, password=%s WHERE id=%s", (name, username, email, pw, session['user_id']))
                db.commit()
            else:
                db.execute("UPDATE users SET name=?, username=?, email=?, password=? WHERE id=?", (name, username, email, pw, session['user_id']))
                db.commit()
                db.close()
            flash('Na-update profile! Nagpalit ka password, login ka ulit.')
            session.clear()
            return redirect('/login')
        else:
            if is_pg():
                cur.execute("UPDATE users SET name=%s, username=%s, email=%s WHERE id=%s", (name, username, email, session['user_id']))
                db.commit()
            else:
                db.execute("UPDATE users SET name=?, username=?, email=? WHERE id=?", (name, username, email, session['user_id']))
                db.commit()
                db.close()
            session['name']=name
            session['email']=email
            flash('Na-update profile!')
            return redirect('/profile')
    if not is_pg():
        db.close()
    return render_template('profile.html', user=user)

@app.route('/fixdb')
def fixdb():
    try:
        init_db()
        return "DB AYOS NA! Punta ka /login - admin@zdspgc.edu.ph / admin123"
    except Exception as e:
        return f"Error: {e}"

with app.app_context():
    try:
        init_db()
        print("ZDSPGC DB INIT SUCCESS!")
    except Exception as e:
        print(f"DB Init Error: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
