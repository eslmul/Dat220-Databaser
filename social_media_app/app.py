from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy import exc as sqlalchemy_exc
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Helper functions to execute SQL queries
def execute_query(query, params=None, fetch_all=False, commit=False):
    with db.engine.connect() as connection:
        if params:
            result = connection.execute(text(query), params)
        else:
            result = connection.execute(text(query))
        
        # For DELETE, UPDATE, INSERT operations
        if commit or query.strip().upper().startswith(('DELETE', 'UPDATE', 'INSERT')):
            connection.commit()
            # For these operations, just return success
            if query.strip().upper().startswith(('DELETE', 'UPDATE', 'INSERT')):
                return True
        
        if fetch_all:
            # Convert SQLAlchemy Row objects to dictionaries
            return [dict(zip(result.keys(), row)) for row in result]
        else:
            # For SELECT operations that return a single row
            try:
                row = result.fetchone()
                if row:
                    return dict(zip(result.keys(), row))
            except sqlalchemy_exc.ResourceClosedError:
                pass  # Handle case where result doesn't have rows
        
        return None

def execute_insert(query, params=None):
    with db.engine.connect() as connection:
        result = connection.execute(text(query), params)
        connection.commit()
        return result.lastrowid

# Home route
@app.route('/')
def index():
    # Get latest posts
    posts = execute_query('''
        SELECT i.innlegg_id, i.innhold, i.opprettet_dato, i.synlighet, 
               b.bruker_id, b.brukernavn, b.profilbilde
        FROM INNLEGG i
        JOIN BRUKERE b ON i.bruker_id = b.bruker_id
        WHERE i.synlighet = 'offentlig'
        ORDER BY i.opprettet_dato DESC
        LIMIT 10
    ''', fetch_all=True)
    
    return render_template('index.html', posts=posts)

# USER ROUTES (CRUD operations)
# List all users
@app.route('/users')
def list_users():
    users = execute_query("SELECT * FROM BRUKERE ORDER BY registrerings_dato DESC", fetch_all=True)
    return render_template('users/list.html', users=users)

# View user profile
@app.route('/users/<int:user_id>')
def view_user(user_id):
    # Get user information
    user = execute_query("SELECT * FROM BRUKERE WHERE bruker_id = :user_id", {"user_id": user_id})
    
    if not user:
        flash('Bruker ikke funnet!', 'danger')
        return redirect(url_for('list_users'))
    
    # Get user's posts
    posts = execute_query('''
        SELECT * FROM INNLEGG 
        WHERE bruker_id = :user_id 
        ORDER BY opprettet_dato DESC
    ''', {"user_id": user_id}, fetch_all=True)
    
    # Get follower count
    follower_count = execute_query('''
        SELECT COUNT(*) as num_followers
        FROM FØLGER
        WHERE følger_bruker_id = :user_id AND status = 'aktiv'
    ''', {"user_id": user_id})
    
    # Get following count
    following_count = execute_query('''
        SELECT COUNT(*) as num_following
        FROM FØLGER
        WHERE følger_id = :user_id AND status = 'aktiv'
    ''', {"user_id": user_id})
    
    return render_template('users/view.html', 
                          user=user, 
                          posts=posts, 
                          follower_count=follower_count["num_followers"],
                          following_count=following_count["num_following"])

# Create new user form
@app.route('/users/create', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        # Get form data
        brukernavn = request.form['brukernavn']
        epost = request.form['epost']
        passord_hash = request.form['passord']  # In production, hash the password
        profilbilde = request.form['profilbilde']
        bio = request.form['bio']
        fødselsdato = request.form['fødselsdato']
        
        # Validate data (including required birthdate)
        if not brukernavn or not epost or not passord_hash or not fødselsdato:
            flash('Brukernavn, e-post, passord og fødselsdato er påkrevd!', 'danger')
            return render_template('users/create.html')
        
        # Check if username or email already exists
        existing_user = execute_query(
            "SELECT * FROM BRUKERE WHERE brukernavn = :brukernavn OR epost = :epost", 
            {"brukernavn": brukernavn, "epost": epost}
        )
        
        if existing_user:
            flash('Brukernavn eller e-post er allerede i bruk!', 'danger')
            return render_template('users/create.html')
        
        # Insert new user
        new_user_id = execute_insert('''
            INSERT INTO BRUKERE 
            (brukernavn, epost, passord_hash, profilbilde, bio, fødselsdato) 
            VALUES (:brukernavn, :epost, :passord_hash, :profilbilde, :bio, :fødselsdato)
        ''', {
            "brukernavn": brukernavn, 
            "epost": epost, 
            "passord_hash": passord_hash, 
            "profilbilde": profilbilde, 
            "bio": bio, 
            "fødselsdato": fødselsdato
        })
        
        flash('Bruker opprettet!', 'success')
        return redirect(url_for('view_user', user_id=new_user_id))
    
    return render_template('users/create.html')

# Edit user
@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    # Get user
    user = execute_query("SELECT * FROM BRUKERE WHERE bruker_id = :user_id", {"user_id": user_id})
    
    if not user:
        flash('Bruker ikke funnet!', 'danger')
        return redirect(url_for('list_users'))
    
    if request.method == 'POST':
        # Get form data
        brukernavn = request.form['brukernavn']
        epost = request.form['epost']
        profilbilde = request.form['profilbilde']
        bio = request.form['bio']
        status = request.form['status']
        
        # Check if username or email already exists for other users
        existing_user = execute_query('''
            SELECT * FROM BRUKERE 
            WHERE (brukernavn = :brukernavn OR epost = :epost) AND bruker_id != :user_id
        ''', {"brukernavn": brukernavn, "epost": epost, "user_id": user_id})
        
        if existing_user:
            flash('Brukernavn eller e-post er allerede i bruk!', 'danger')
            return render_template('users/edit.html', user=user)
        
        # Update user
        execute_query('''
            UPDATE BRUKERE 
            SET brukernavn = :brukernavn, epost = :epost, profilbilde = :profilbilde, bio = :bio, status = :status 
            WHERE bruker_id = :user_id
        ''', {
            "brukernavn": brukernavn, 
            "epost": epost, 
            "profilbilde": profilbilde, 
            "bio": bio, 
            "status": status, 
            "user_id": user_id
        }, commit=True)
        
        flash('Bruker oppdatert!', 'success')
        return redirect(url_for('view_user', user_id=user_id))
    
    return render_template('users/edit.html', user=user)

# Delete user
@app.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    # Check if user exists
    user = execute_query("SELECT * FROM BRUKERE WHERE bruker_id = :user_id", {"user_id": user_id})
    
    if not user:
        flash('Bruker ikke funnet!', 'danger')
        return redirect(url_for('list_users'))
    
    # Delete user (this will cascade to related records due to FK constraints)
    execute_query("DELETE FROM BRUKERE WHERE bruker_id = :user_id", {"user_id": user_id}, commit=True)
    
    flash('Bruker slettet!', 'success')
    return redirect(url_for('list_users'))

# POST ROUTES (CRUD operations)
# List all posts
@app.route('/posts')
def list_posts():
    posts = execute_query('''
        SELECT i.innlegg_id, i.innhold, i.opprettet_dato, i.synlighet, 
               b.bruker_id, b.brukernavn, b.profilbilde
        FROM INNLEGG i
        JOIN BRUKERE b ON i.bruker_id = b.bruker_id
        ORDER BY i.opprettet_dato DESC
    ''', fetch_all=True)
    
    return render_template('posts/list.html', posts=posts)

# View post
@app.route('/posts/<int:post_id>')
def view_post(post_id):
    # Get post with user information
    post = execute_query('''
        SELECT i.*, b.brukernavn, b.profilbilde 
        FROM INNLEGG i
        JOIN BRUKERE b ON i.bruker_id = b.bruker_id
        WHERE i.innlegg_id = :post_id
    ''', {"post_id": post_id})
    
    if not post:
        flash('Innlegg ikke funnet!', 'danger')
        return redirect(url_for('list_posts'))
    
    # Get comments for this post
    comments = execute_query('''
        SELECT k.*, b.brukernavn, b.profilbilde 
        FROM KOMMENTARER k
        JOIN BRUKERE b ON k.bruker_id = b.bruker_id
        WHERE k.innlegg_id = :post_id
        ORDER BY k.opprettet_dato
    ''', {"post_id": post_id}, fetch_all=True)
    
    # Get reactions count
    reactions = execute_query('''
        SELECT reaksjon_type, COUNT(*) as count
        FROM REAKSJONER
        WHERE innlegg_id = :post_id
        GROUP BY reaksjon_type
    ''', {"post_id": post_id}, fetch_all=True)
    
    return render_template('posts/view.html', 
                          post=post, 
                          comments=comments, 
                          reactions=reactions)

# Create new post
@app.route('/posts/create', methods=['GET', 'POST'])
def create_post():
    # In a real app, check if user is logged in
    # This is a simplified version
    if request.method == 'POST':
        # Get form data
        innhold = request.form['innhold']
        synlighet = request.form['synlighet']
        bruker_id = request.form['bruker_id']  # In real app, get from session
        
        # Basic validation
        if not innhold or not bruker_id:
            flash('Innhold og bruker-ID er påkrevd!', 'danger')
            
            # Get all users for dropdown
            users = execute_query("SELECT bruker_id, brukernavn FROM BRUKERE", fetch_all=True)
            
            return render_template('posts/create.html', users=users)
        
        # Insert new post
        new_post_id = execute_insert('''
            INSERT INTO INNLEGG (innhold, synlighet, bruker_id)
            VALUES (:innhold, :synlighet, :bruker_id)
        ''', {"innhold": innhold, "synlighet": synlighet, "bruker_id": bruker_id})
        
        flash('Innlegg opprettet!', 'success')
        return redirect(url_for('view_post', post_id=new_post_id))
    
    # Get all users for dropdown
    users = execute_query("SELECT bruker_id, brukernavn FROM BRUKERE", fetch_all=True)
    
    return render_template('posts/create.html', users=users)

# Edit post
@app.route('/posts/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    # Get post
    post = execute_query("SELECT * FROM INNLEGG WHERE innlegg_id = :post_id", {"post_id": post_id})
    
    if not post:
        flash('Innlegg ikke funnet!', 'danger')
        return redirect(url_for('list_posts'))
    
    if request.method == 'POST':
        # Get form data
        innhold = request.form['innhold']
        synlighet = request.form['synlighet']
        
        # Update post
        execute_query('''
            UPDATE INNLEGG
            SET innhold = :innhold, synlighet = :synlighet
            WHERE innlegg_id = :post_id
        ''', {"innhold": innhold, "synlighet": synlighet, "post_id": post_id}, commit=True)
        
        flash('Innlegg oppdatert!', 'success')
        return redirect(url_for('view_post', post_id=post_id))
    
    return render_template('posts/edit.html', post=post)

# Delete post
@app.route('/posts/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    # Check if post exists
    post = execute_query("SELECT * FROM INNLEGG WHERE innlegg_id = :post_id", {"post_id": post_id})
    
    if not post:
        flash('Innlegg ikke funnet!', 'danger')
        return redirect(url_for('list_posts'))
    
    # Delete post (this will cascade to related records due to FK constraints)
    execute_query("DELETE FROM INNLEGG WHERE innlegg_id = :post_id", {"post_id": post_id}, commit=True)
    
    flash('Innlegg slettet!', 'success')
    return redirect(url_for('list_posts'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)