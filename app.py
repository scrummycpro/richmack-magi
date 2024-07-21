from flask import Flask, render_template, request, redirect, url_for, flash, g, send_from_directory, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
from flask_bootstrap import Bootstrap
import os
from werkzeug.utils import secure_filename
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a random secret key each time the app starts
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DATABASE = 'responses.db'
NOTES_DATABASE = 'notes.db'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Update credentials to the preferred ones
users = {'richmack': User(id=1, username='Richmack', password='abasiscus')}  # Hardcoded user with lowercase key for case-insensitive match

@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if user.id == int(user_id):
            return user
    return None

def get_db(database):
    db = getattr(g, f'_database_{database}', None)
    if db is None:
        db = sqlite3.connect(database)
        setattr(g, f'_database_{database}', db)
    return db

@app.teardown_appcontext
def close_connection(exception):
    for db_attr in ['_database_responses.db', '_database_notes.db']:
        db = getattr(g, db_attr, None)
        if db is not None:
            db.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if current_user.is_authenticated:
        db = get_db(NOTES_DATABASE)
        cursor = db.cursor()
        cursor.execute("SELECT id, title, note, filename FROM notes")
        notes = cursor.fetchall()
        return render_template('index.html', notes=notes)
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        user = users.get(username)
        if user and user.password == password:
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        query = request.form['query']
        table = request.form['table']
        db = get_db(DATABASE)
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM {table} WHERE prompt LIKE ? OR response LIKE ?", ('%' + query + '%', '%' + query + '%'))
        results = cursor.fetchall()
        if 'export' in request.form:
            response_content = "\n\n".join([f"Prompt: {result[2]}\nResponse: {result[3]}" for result in results])
            response = make_response(response_content)
            response.headers["Content-Disposition"] = "attachment; filename=search_results.txt"
            return response
        return render_template('search.html', results=results, query=query, table=table)
    return render_template('search.html', results=None)

@app.route('/add_note', methods=['GET', 'POST'])
@login_required
def add_note():
    if request.method == 'POST':
        title = request.form['title']
        note = request.form['note']
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None
        db = get_db(NOTES_DATABASE)
        cursor = db.cursor()
        cursor.execute("INSERT INTO notes (title, note, filename) VALUES (?, ?, ?)", (title, note, filename))
        db.commit()
        flash('Note added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_note.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/note/<int:note_id>')
@login_required
def note_detail(note_id):
    db = get_db(NOTES_DATABASE)
    cursor = db.cursor()
    cursor.execute("SELECT id, title, note, filename FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    if note:
        return render_template('note_detail.html', note=note)
    else:
        flash('Note not found', 'danger')
        return redirect(url_for('index'))

@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    db = get_db(NOTES_DATABASE)
    cursor = db.cursor()
    if request.method == 'POST':
        title = request.form['title']
        note = request.form['note']
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor.execute("UPDATE notes SET title = ?, note = ?, filename = ? WHERE id = ?", (title, note, filename, note_id))
        else:
            cursor.execute("UPDATE notes SET title = ?, note = ? WHERE id = ?", (title, note, note_id))
        db.commit()
        flash('Note updated successfully!', 'success')
        return redirect(url_for('note_detail', note_id=note_id))
    else:
        cursor.execute("SELECT id, title, note, filename FROM notes WHERE id = ?", (note_id,))
        note = cursor.fetchone()
        if note:
            return render_template('edit_note.html', note=note)
        else:
            flash('Note not found', 'danger')
            return redirect(url_for('index'))

@app.route('/export_note/<int:note_id>')
@login_required
def export_note(note_id):
    db = get_db(NOTES_DATABASE)
    cursor = db.cursor()
    cursor.execute("SELECT id, title, note, filename FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    if note:
        response = make_response(f"Title: {note[1]}\n\nNote:\n{note[2]}")
        response.headers["Content-Disposition"] = f"attachment; filename=note_{note_id}.txt"
        return response
    else:
        flash('Note not found', 'danger')
        return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    # Initialize the notes database if it doesn't exist
    with sqlite3.connect(NOTES_DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            note TEXT NOT NULL,
            filename TEXT
        );
        ''')
        conn.commit()
    app.run(debug=True)