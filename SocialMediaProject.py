from flask import Flask, render_template_string, request, redirect, url_for, session, g
import sqlite3

app = Flask(__name__)
app.secret_key = 'socialmediasecretkey'
DATABASE = 'social_media.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                likes INTEGER DEFAULT 0,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS follows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower TEXT NOT NULL,
                following TEXT NOT NULL
            )
        ''')
        db.commit()

init_db()

# HTML & CSS Template
TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Mini Social Media Platform</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f0f2f5; color: #333; }
        header { background: #1877f2; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; }
        nav a { color: white; margin-left: 15px; text-decoration: none; font-weight: bold; }
        .container { max-width: 700px; margin: 20px auto; padding: 0 15px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); margin-bottom: 15px; }
        textarea, input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ccd0d5; border-radius: 4px; box-sizing: border-box; }
        .btn { background: #1877f2; color: white; border: none; padding: 8px 16px; cursor: pointer; border-radius: 4px; font-weight: bold; text-decoration: none; display: inline-block; }
        .btn:hover { background: #166fe5; }
        .btn-danger { background: #e41e3f; }
        .btn-danger:hover { background: #d01d39; }
        .post-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .comment-box { margin-top: 10px; padding-left: 15px; border-left: 2px solid #e4e6eb; font-size: 0.9rem; }
    </style>
</head>
<body>
    <header>
        <h2>🌐 MiniSocial</h2>
        <nav>
            <a href="{{ url_for('index') }}">Feed</a>
            {% if session.get('user') %}
                <a href="{{ url_for('profile', username=session['user']) }}">My Profile</a>
                <a href="{{ url_for('logout') }}">Logout ({{ session['user'] }})</a>
            {% else %}
                <a href="{{ url_for('login') }}">Login</a>
                <a href="{{ url_for('register') }}">Register</a>
            {% endif %}
        </nav>
    </header>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

INDEX_TEMPLATE = TEMPLATE.replace('{% block content %}{% endblock %}', '''
    {% if session.get('user') %}
    <div class="card">
        <h3>Create Post</h3>
        <form method="POST" action="{{ url_for('create_post') }}">
            <textarea name="content" rows="3" placeholder="What's on your mind?" required></textarea>
            <button type="submit" class="btn">Post</button>
        </form>
    </div>
    {% endif %}

    <h2>News Feed</h2>
    {% for post in posts %}
    <div class="card">
        <div class="post-header">
            <strong><a href="{{ url_for('profile', username=post['username']) }}" style="color:#1877f2; text-decoration:none;">@{{ post['username'] }}</a></strong>
            <small style="color: #65676b;">{{ post['date'] }}</small>
        </div>
        <p>{{ post['content'] }}</p>
        <hr style="border:0; border-top:1px solid #eee; margin:10px 0;">
        <div style="display:flex; gap: 15px; align-items: center;">
            <form method="POST" action="{{ url_for('like_post', post_id=post['id']) }}" style="margin:0;">
                <button type="submit" class="btn" style="background:#e4e6eb; color:#050505;">👍 Like ({{ post['likes'] }})</button>
            </form>
        </div>

        <div style="margin-top: 15px;">
            <h4>Comments</h4>
            {% for comment in comments[post['id']] %}
            <div class="comment-box">
                <strong>@{{ comment['username'] }}:</strong> {{ comment['content'] }}
            </div>
            {% endfor %}
            
            {% if session.get('user') %}
            <form method="POST" action="{{ url_for('add_comment', post_id=post['id']) }}" style="margin-top: 10px; display:flex; gap:5px;">
                <input type="text" name="content" placeholder="Write a comment..." required style="margin:0;">
                <button type="submit" class="btn" style="padding: 6px 12px;">Comment</button>
            </form>
            {% endif %}
        </div>
    </div>
    {% endfor %}
''')

PROFILE_TEMPLATE = TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <div class="card" style="text-align: center;">
        <h2>@{{ profile_user }}'s Profile</h2>
        <p>Followers: {{ followers_count }} | Following: {{ following_count }}</p>
        {% if session.get('user') and session['user'] != profile_user %}
            <form method="POST" action="{{ url_for('toggle_follow', username=profile_user) }}">
                <button type="submit" class="btn {% if is_following %}btn-danger{% endif %}">
                    {% if is_following %}Unfollow{% else %}Follow{% endif %}
                </button>
            </form>
        {% endif %}
    </div>

    <h3>Posts by @{{ profile_user }}</h3>
    {% for post in posts %}
    <div class="card">
        <small style="color: #65676b;">{{ post['date'] }}</small>
        <p>{{ post['content'] }}</p>
        <p><strong>👍 Likes: {{ post['likes'] }}</strong></p>
    </div>
    {% endfor %}
''')

AUTH_TEMPLATE = TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <div class="card" style="max-width: 400px; margin: 40px auto;">
        <h2>{{ title }}</h2>
        <form method="POST">
            <label>Username</label>
            <input type="text" name="username" required>
            <label>Password</label>
            <input type="password" name="password" required>
            <button type="submit" class="btn" style="width:100%;">{{ title }}</button>
        </form>
    </div>
''')

@app.route('/')
def index():
    db = get_db()
    posts = db.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    
    # Fetch comments for each post
    comments = {}
    for post in posts:
        post_comments = db.execute("SELECT * FROM comments WHERE post_id = ? ORDER BY id ASC", (post['id'],)).fetchall()
        comments[post['id']] = post_comments
        
    return render_template_string(INDEX_TEMPLATE, posts=posts, comments=comments)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists!"
    return render_template_string(AUTH_TEMPLATE, title="Register")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        if user:
            session['user'] = username
            return redirect(url_for('index'))
        return "Invalid credentials!"
    return render_template_string(AUTH_TEMPLATE, title="Login")

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/post', methods=['POST'])
def create_post():
    if 'user' not in session:
        return redirect(url_for('login'))
    content = request.form['content']
    db = get_db()
    db.execute("INSERT INTO posts (username, content) VALUES (?, ?)", (session['user'], content))
    db.commit()
    return redirect(url_for('index'))

@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    db = get_db()
    db.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    db.commit()
    return redirect(url_for('index'))

@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    content = request.form['content']
    db = get_db()
    db.execute("INSERT INTO comments (post_id, username, content) VALUES (?, ?, ?)", (post_id, session['user'], content))
    db.commit()
    return redirect(url_for('index'))

@app.route('/profile/<username>')
def profile(username):
    db = get_db()
    posts = db.execute("SELECT * FROM posts WHERE username = ? ORDER BY id DESC", (username,)).fetchall()
    
    followers_count = db.execute("SELECT COUNT(*) FROM follows WHERE following = ?", (username,)).fetchone()[0]
    following_count = db.execute("SELECT COUNT(*) FROM follows WHERE follower = ?", (username,)).fetchone()[0]
    
    is_following = False
    if 'user' in session:
        check = db.execute("SELECT * FROM follows WHERE follower = ? AND following = ?", (session['user'], username)).fetchone()
        if check:
            is_following = True
            
    return render_template_string(PROFILE_TEMPLATE, profile_user=username, posts=posts, followers_count=followers_count, following_count=following_count, is_following=is_following)

@app.route('/follow/<username>', methods=['POST'])
def toggle_follow(username):
    if 'user' not in session:
        return redirect(url_for('login'))
    current_user = session['user']
    db = get_db()
    
    existing = db.execute("SELECT * FROM follows WHERE follower = ? AND following = ?", (current_user, username)).fetchone()
    if existing:
        db.execute("DELETE FROM follows WHERE follower = ? AND following = ?", (current_user, username))
    else:
        db.execute("INSERT INTO follows (follower, following) VALUES (?, ?)", (current_user, username))
    db.commit()
    return redirect(url_for('profile', username=username))

if __name__ == '__main__':
    app.run(debug=True, port=5001)