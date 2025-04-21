from flask import Flask, render_template, request, redirect, url_for, flash, session
from db_config import Database, init_db, add_sample_data
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages and sessions

# Helper function to convert SQLite rows to dictionaries with proper datetime objects
def format_date_fields(item, date_fields=None):
    if not item:
        return None
        
    # Convert Row to dict if it's not already
    if not isinstance(item, dict):
        item = dict(item)
        
    # Process date fields if specified
    if date_fields:
        for field in date_fields:
            if field in item and item[field]:
                # Parse the date string into a datetime object
                try:
                    if 'T' in item[field]:  # ISO format
                        item[field] = datetime.fromisoformat(item[field].replace('Z', '+00:00'))
                    else:  # SQLite default format
                        item[field] = datetime.strptime(item[field], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    try:
                        # Try date-only format
                        item[field] = datetime.strptime(item[field], '%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass  # Keep original if parsing fails
    return item

# Initialize database on startup
def initialize_database():
    init_db()
    add_sample_data()

# Call initialization function during startup
with app.app_context():
    initialize_database()

# Routes for Users (BRUKERE)
@app.route('/')
def index():
    return render_template('index.html')

# READ - List all users
@app.route('/users')
def list_users():
    with Database() as db:
        users = db.fetchall("SELECT * FROM BRUKERE")
        # Format date fields
        users = [format_date_fields(user, ['registrerings_dato', 'fødselsdato']) for user in users]
    return render_template('users/list.html', users=users)

# READ - View user profile
@app.route('/users/<int:user_id>')
def view_user(user_id):
    with Database() as db:
        user = db.fetchone("SELECT * FROM BRUKERE WHERE bruker_id = ?", (user_id,))
        if user:
            user = format_date_fields(user, ['registrerings_dato', 'fødselsdato'])
            # Get user's posts
            posts = db.fetchall("SELECT * FROM INNLEGG WHERE bruker_id = ? ORDER BY opprettet_dato DESC", (user_id,))
            posts = [format_date_fields(post, ['opprettet_dato', 'oppdatert_dato']) for post in posts]
            
            # Get user's followers count
            followers = db.fetchone("SELECT COUNT(*) as count FROM FØLGER WHERE følger_bruker_id = ? AND status = 'aktiv'", (user_id,))
            # Get user's following count
            following = db.fetchone("SELECT COUNT(*) as count FROM FØLGER WHERE følger_id = ? AND status = 'aktiv'", (user_id,))
            return render_template('users/view.html', user=user, posts=posts, 
                                followers=followers['count'], following=following['count'])
    flash('User not found', 'danger')
    return redirect(url_for('list_users'))

# CREATE - Show user creation form
@app.route('/users/create', methods=['GET'])
def show_create_user():
    return render_template('users/create.html')

# CREATE - Process user creation
@app.route('/users/create', methods=['POST'])
def create_user():
    username = request.form['brukernavn']
    email = request.form['epost']
    password_hash = request.form['passord_hash']  # In a real app, you'd hash this
    bio = request.form['bio']
    birth_date = request.form['fødselsdato'] if request.form['fødselsdato'] else None
    
    try:
        with Database() as db:
            user_id = db.execute(
                "INSERT INTO BRUKERE (brukernavn, epost, passord_hash, bio, fødselsdato, status) "
                "VALUES (?, ?, ?, ?, ?, 'aktiv')",
                (username, email, password_hash, bio, birth_date)
            )
        flash('User created successfully!', 'success')
        return redirect(url_for('view_user', user_id=user_id))
    except Exception as e:
        flash(f'Error creating user: {str(e)}', 'danger')
        return render_template('users/create.html')

# UPDATE - Show user edit form
@app.route('/users/<int:user_id>/edit', methods=['GET'])
def show_edit_user(user_id):
    with Database() as db:
        user = db.fetchone("SELECT * FROM BRUKERE WHERE bruker_id = ?", (user_id,))
        user = format_date_fields(user, ['registrerings_dato', 'fødselsdato'])
    if user:
        return render_template('users/edit.html', user=user)
    flash('User not found', 'danger')
    return redirect(url_for('list_users'))

# UPDATE - Process user update
@app.route('/users/<int:user_id>/edit', methods=['POST'])
def edit_user(user_id):
    with Database() as db:
        # Check if user exists
        user = db.fetchone("SELECT * FROM BRUKERE WHERE bruker_id = ?", (user_id,))
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('list_users'))
        
        bio = request.form['bio']
        status = request.form['status']
        
        # Update user data
        db.execute(
            "UPDATE BRUKERE SET bio = ?, status = ? WHERE bruker_id = ?",
            (bio, status, user_id)
        )
        
    flash('User updated successfully!', 'success')
    return redirect(url_for('view_user', user_id=user_id))

# DELETE - Delete user
@app.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    with Database() as db:
        db.execute("DELETE FROM BRUKERE WHERE bruker_id = ?", (user_id,))
    flash('User deleted successfully!', 'success')
    return redirect(url_for('list_users'))

# Routes for Posts (INNLEGG)
# READ - List all posts
@app.route('/posts')
def list_posts():
    with Database() as db:
        # Join with users to get username
        posts = db.fetchall("""
            SELECT i.*, b.brukernavn 
            FROM INNLEGG i 
            JOIN BRUKERE b ON i.bruker_id = b.bruker_id 
            ORDER BY i.opprettet_dato DESC
        """)
        posts = [format_date_fields(post, ['opprettet_dato', 'oppdatert_dato']) for post in posts]
    return render_template('posts/list.html', posts=posts)

# READ - View single post with comments
@app.route('/posts/<int:post_id>')
def view_post(post_id):
    with Database() as db:
        # Get post with user info
        post = db.fetchone("""
            SELECT i.*, b.brukernavn, b.profilbilde
            FROM INNLEGG i 
            JOIN BRUKERE b ON i.bruker_id = b.bruker_id 
            WHERE i.innlegg_id = ?
        """, (post_id,))
        
        if not post:
            flash('Post not found', 'danger')
            return redirect(url_for('list_posts'))
            
        post = format_date_fields(post, ['opprettet_dato', 'oppdatert_dato'])
            
        # Get comments for this post with user info
        comments = db.fetchall("""
            SELECT k.*, b.brukernavn, b.profilbilde
            FROM KOMMENTARER k
            JOIN BRUKERE b ON k.bruker_id = b.bruker_id
            WHERE k.innlegg_id = ?
            ORDER BY k.opprettet_dato ASC
        """, (post_id,))
        comments = [format_date_fields(comment, ['opprettet_dato']) for comment in comments]
        
        # Get tags for this post
        tags = db.fetchall("""
            SELECT t.* 
            FROM TAGGER t
            JOIN INNLEGG_TAGGER it ON t.tag_id = it.tag_id
            WHERE it.innlegg_id = ?
        """, (post_id,))
        
        # Get reaction counts
        reactions = db.fetchone("""
            SELECT COUNT(*) as count, reaksjon_type
            FROM REAKSJONER 
            WHERE innlegg_id = ?
            GROUP BY reaksjon_type
        """, (post_id,))
        
        return render_template('posts/view.html', post=post, comments=comments, 
                               tags=tags, reactions=reactions)

# CREATE - Show post creation form
@app.route('/posts/create', methods=['GET'])
def show_create_post():
    with Database() as db:
        users = db.fetchall("SELECT bruker_id, brukernavn FROM BRUKERE WHERE status = 'aktiv'")
        tags = db.fetchall("SELECT * FROM TAGGER")
    return render_template('posts/create.html', users=users, tags=tags)

# CREATE - Process post creation
@app.route('/posts/create', methods=['POST'])
def create_post():
    user_id = request.form['bruker_id']
    content = request.form['innhold']
    visibility = request.form['synlighet']
    tag_ids = request.form.getlist('tags')  # Get list of selected tag IDs
    
    try:
        with Database() as db:
            # Insert post
            post_id = db.execute(
                "INSERT INTO INNLEGG (innhold, opprettet_dato, synlighet, bruker_id) "
                "VALUES (?, datetime('now'), ?, ?)",
                (content, visibility, user_id)
            )
            
            # Insert tags if any selected
            for tag_id in tag_ids:
                db.execute(
                    "INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES (?, ?)",
                    (post_id, tag_id)
                )
                
        flash('Post created successfully!', 'success')
        return redirect(url_for('view_post', post_id=post_id))
    except Exception as e:
        flash(f'Error creating post: {str(e)}', 'danger')
        return redirect(url_for('show_create_post'))

# UPDATE - Show post edit form
@app.route('/posts/<int:post_id>/edit', methods=['GET'])
def show_edit_post(post_id):
    with Database() as db:
        post = db.fetchone("SELECT * FROM INNLEGG WHERE innlegg_id = ?", (post_id,))
        if not post:
            flash('Post not found', 'danger')
            return redirect(url_for('list_posts'))
            
        post = format_date_fields(post, ['opprettet_dato', 'oppdatert_dato'])
            
        # Get all available tags
        all_tags = db.fetchall("SELECT * FROM TAGGER")
        
        # Get currently selected tags for this post
        post_tags = db.fetchall("""
            SELECT tag_id FROM INNLEGG_TAGGER 
            WHERE innlegg_id = ?
        """, (post_id,))
        
        # Convert to list of tag IDs for easy checking in template
        selected_tag_ids = [tag['tag_id'] for tag in post_tags]
        
    return render_template('posts/edit.html', post=post, all_tags=all_tags, 
                           selected_tag_ids=selected_tag_ids)

# UPDATE - Process post update
@app.route('/posts/<int:post_id>/edit', methods=['POST'])
def edit_post(post_id):
    content = request.form['innhold']
    visibility = request.form['synlighet']
    tag_ids = request.form.getlist('tags')  # Get list of selected tag IDs
    
    try:
        with Database() as db:
            # Update post
            db.execute(
                "UPDATE INNLEGG SET innhold = ?, synlighet = ?, oppdatert_dato = datetime('now') WHERE innlegg_id = ?",
                (content, visibility, post_id)
            )
            
            # Delete all existing tag associations
            db.execute("DELETE FROM INNLEGG_TAGGER WHERE innlegg_id = ?", (post_id,))
            
            # Insert new tag associations
            for tag_id in tag_ids:
                db.execute(
                    "INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES (?, ?)",
                    (post_id, tag_id)
                )
                
        flash('Post updated successfully!', 'success')
        return redirect(url_for('view_post', post_id=post_id))
    except Exception as e:
        flash(f'Error updating post: {str(e)}', 'danger')
        return redirect(url_for('show_edit_post', post_id=post_id))

# DELETE - Delete post
@app.route('/posts/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    with Database() as db:
        db.execute("DELETE FROM INNLEGG WHERE innlegg_id = ?", (post_id,))
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('list_posts'))

if __name__ == '__main__':
    app.run(debug=True)