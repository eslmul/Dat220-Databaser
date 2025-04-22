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

@app.route('/')
def index():
    with Database() as db:
        newest_posts = db.fetchall("""
            SELECT i.*, b.brukernavn 
            FROM INNLEGG i 
            JOIN BRUKERE b ON i.bruker_id = b.bruker_id 
            ORDER BY i.opprettet_dato DESC LIMIT 5
        """)
        newest_posts = [format_date_fields(post, ['opprettet_dato', 'oppdatert_dato']) for post in newest_posts]
        
        newest_users = db.fetchall("""
            SELECT * FROM BRUKERE
            ORDER BY registrerings_dato DESC LIMIT 5
        """)
        newest_users = [format_date_fields(user, ['registrerings_dato', 'fødselsdato']) for user in newest_users]
    
    return render_template('index.html', newest_posts=newest_posts, newest_users=newest_users)

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

@app.route('/popular_posts')
def popular_posts():
    with Database() as db:
        posts = db.fetchall("""
            SELECT 
                i.innlegg_id,
                i.innhold,
                i.opprettet_dato,
                i.synlighet,
                b.bruker_id,
                b.brukernavn,
                b.profilbilde,
                t.navn AS tag_navn,
                COUNT(DISTINCT r.reaksjon_id) AS antall_reaksjoner,
                COUNT(DISTINCT k.kommentar_id) AS antall_kommentarer
            FROM INNLEGG i
            JOIN BRUKERE b ON i.bruker_id = b.bruker_id
            LEFT JOIN INNLEGG_TAGGER it ON i.innlegg_id = it.innlegg_id
            LEFT JOIN TAGGER t ON it.tag_id = t.tag_id
            LEFT JOIN REAKSJONER r ON i.innlegg_id = r.innlegg_id
            LEFT JOIN KOMMENTARER k ON i.innlegg_id = k.innlegg_id
            WHERE i.synlighet = 'offentlig'
            GROUP BY i.innlegg_id, t.tag_id
            ORDER BY antall_reaksjoner DESC, i.opprettet_dato DESC
            LIMIT 10
        """)
        posts = [format_date_fields(post, ['opprettet_dato']) for post in posts]
    return render_template('analytics/popular_posts.html', posts=posts)

# Route for user engagement analysis
@app.route('/user_engagement')
def user_engagement():
    with Database() as db:
        users = db.fetchall("""
            SELECT 
                b.bruker_id,
                b.brukernavn,
                b.profilbilde,
                b.status,
                COUNT(DISTINCT i.innlegg_id) AS antall_innlegg,
                COUNT(DISTINCT k.kommentar_id) AS antall_kommentarer,
                COUNT(DISTINCT r.reaksjon_id) AS antall_reaksjoner,
                COUNT(DISTINCT f.følge_id) AS antall_følger,
                (SELECT COUNT(*) FROM FØLGER WHERE følger_bruker_id = b.bruker_id) AS antall_følgere,
                MAX(i.opprettet_dato) AS siste_aktivitet
            FROM BRUKERE b
            LEFT JOIN INNLEGG i ON b.bruker_id = i.bruker_id
            LEFT JOIN KOMMENTARER k ON b.bruker_id = k.bruker_id
            LEFT JOIN REAKSJONER r ON b.bruker_id = r.bruker_id
            LEFT JOIN FØLGER f ON b.bruker_id = f.følger_id
            GROUP BY b.bruker_id
            ORDER BY (antall_innlegg + antall_kommentarer + antall_reaksjoner) DESC
        """)
        users = [format_date_fields(user, ['siste_aktivitet']) for user in users]
    return render_template('analytics/user_engagement.html', users=users)

# Route for displaying platform statistics
@app.route('/platform_stats')
def platform_stats():
    with Database() as db:
        stats = db.fetchone("""
            SELECT
                COUNT(DISTINCT b.bruker_id) AS total_users,
                COUNT(DISTINCT i.innlegg_id) AS total_posts,
                COUNT(DISTINCT k.kommentar_id) AS total_comments,
                COUNT(DISTINCT r.reaksjon_id) AS total_reactions,
                COUNT(DISTINCT t.tag_id) AS total_tags,
                (SELECT COUNT(*) FROM FØLGER) AS total_follows,
                (SELECT COUNT(*) FROM MELDINGER) AS total_messages,
                ROUND(AVG(posts_per_user), 2) AS avg_posts_per_user,
                ROUND(AVG(comments_per_user), 2) AS avg_comments_per_user,
                ROUND(AVG(reactions_per_user), 2) AS avg_reactions_per_user
            FROM BRUKERE b
            LEFT JOIN (
                SELECT bruker_id, COUNT(*) as posts_per_user 
                FROM INNLEGG 
                GROUP BY bruker_id
            ) user_posts ON b.bruker_id = user_posts.bruker_id
            LEFT JOIN (
                SELECT bruker_id, COUNT(*) as comments_per_user 
                FROM KOMMENTARER 
                GROUP BY bruker_id
            ) user_comments ON b.bruker_id = user_comments.bruker_id
            LEFT JOIN (
                SELECT bruker_id, COUNT(*) as reactions_per_user 
                FROM REAKSJONER 
                GROUP BY bruker_id
            ) user_reactions ON b.bruker_id = user_reactions.bruker_id
            LEFT JOIN INNLEGG i ON 1=1
            LEFT JOIN KOMMENTARER k ON 1=1
            LEFT JOIN REAKSJONER r ON 1=1
            LEFT JOIN TAGGER t ON 1=1
        """)
    return render_template('analytics/platform_stats.html', stats=stats)

# Route for post engagement metrics
@app.route('/post_engagement')
def post_engagement():
    with Database() as db:
        metrics = db.fetchone("""
            SELECT
                COUNT(*) AS total_posts,
                ROUND(AVG(comment_count), 2) AS avg_comments_per_post,
                ROUND(AVG(reaction_count), 2) AS avg_reactions_per_post,
                MAX(comment_count) AS most_commented,
                MAX(reaction_count) AS most_reacted,
                (SELECT i.innhold FROM INNLEGG i 
                 LEFT JOIN (SELECT innlegg_id, COUNT(*) as cnt FROM KOMMENTARER GROUP BY innlegg_id) kc ON i.innlegg_id = kc.innlegg_id 
                 ORDER BY kc.cnt DESC LIMIT 1) AS most_commented_post,
                (SELECT i.innhold FROM INNLEGG i 
                 LEFT JOIN (SELECT innlegg_id, COUNT(*) as cnt FROM REAKSJONER WHERE innlegg_id IS NOT NULL GROUP BY innlegg_id) rc ON i.innlegg_id = rc.innlegg_id 
                 ORDER BY rc.cnt DESC LIMIT 1) AS most_reacted_post
            FROM (
                SELECT 
                    i.innlegg_id,
                    (SELECT COUNT(*) FROM KOMMENTARER k WHERE k.innlegg_id = i.innlegg_id) AS comment_count,
                    (SELECT COUNT(*) FROM REAKSJONER r WHERE r.innlegg_id = i.innlegg_id) AS reaction_count
                FROM INNLEGG i
            ) post_stats
        """)
    return render_template('analytics/post_engagement.html', metrics=metrics)

@app.route('/search', methods=['GET'])
def search():
    # Get filter parameters from request
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    user_id = request.args.get('user_id', '')
    tag_id = request.args.get('tag_id', '')
    visibility = request.args.get('visibility', '')
    search_term = request.args.get('search_term', '')
    
    # Construct base query
    base_query = """
        SELECT i.*, b.brukernavn, b.profilbilde,
               (SELECT COUNT(*) FROM KOMMENTARER k WHERE k.innlegg_id = i.innlegg_id) AS comment_count,
               (SELECT COUNT(*) FROM REAKSJONER r WHERE r.innlegg_id = i.innlegg_id) AS reaction_count,
               GROUP_CONCAT(t.navn, ', ') as tags
        FROM INNLEGG i
        JOIN BRUKERE b ON i.bruker_id = b.bruker_id
        LEFT JOIN INNLEGG_TAGGER it ON i.innlegg_id = it.innlegg_id
        LEFT JOIN TAGGER t ON it.tag_id = t.tag_id
    """
    
    # Add filters
    where_clauses = []
    query_params = []
    
    if start_date:
        where_clauses.append("i.opprettet_dato >= ?")
        query_params.append(start_date)
    
    if end_date:
        where_clauses.append("i.opprettet_dato <= ?")
        query_params.append(end_date + " 23:59:59")  # Include the whole day
    
    if user_id:
        where_clauses.append("i.bruker_id = ?")
        query_params.append(user_id)
    
    if tag_id:
        where_clauses.append("it.tag_id = ?")
        query_params.append(tag_id)
    
    if visibility:
        where_clauses.append("i.synlighet = ?")
        query_params.append(visibility)
        
    if search_term:
        where_clauses.append("i.innhold LIKE ?")
        query_params.append(f"%{search_term}%")
    
    # Combine where clauses
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    
    # Add group by and order by
    base_query += " GROUP BY i.innlegg_id ORDER BY i.opprettet_dato DESC"
    
    # Get search results
    with Database() as db:
        results = []
        
        if any([start_date, end_date, user_id, tag_id, visibility, search_term]):
            # Only execute the query if at least one filter is applied
            results = db.fetchall(base_query, query_params)
            results = [format_date_fields(result, ['opprettet_dato', 'oppdatert_dato']) for result in results]
        
        # Get all users and tags for the filter form
        users = db.fetchall("SELECT bruker_id, brukernavn FROM BRUKERE ORDER BY brukernavn")
        tags = db.fetchall("SELECT tag_id, navn FROM TAGGER ORDER BY navn")
    
    return render_template('search/results.html', 
                          results=results, 
                          users=users,
                          tags=tags,
                          filters={
                              'start_date': start_date,
                              'end_date': end_date,
                              'user_id': user_id,
                              'tag_id': tag_id,
                              'visibility': visibility,
                              'search_term': search_term
                          })

# Route for tag popularity analysis
@app.route('/tag_analysis')
def tag_analysis():
    with Database() as db:
        tags = db.fetchall("""
            SELECT 
                t.tag_id,
                t.navn,
                COUNT(it.innlegg_id) AS antall_innlegg,
                COUNT(DISTINCT i.bruker_id) AS antall_brukere,
                MIN(i.opprettet_dato) AS første_bruk,
                MAX(i.opprettet_dato) AS siste_bruk
            FROM TAGGER t
            LEFT JOIN INNLEGG_TAGGER it ON t.tag_id = it.tag_id
            LEFT JOIN INNLEGG i ON it.innlegg_id = i.innlegg_id
            GROUP BY t.tag_id, t.navn
            ORDER BY antall_innlegg DESC
        """)
        tags = [format_date_fields(tag, ['første_bruk', 'siste_bruk']) for tag in tags]
    return render_template('analytics/tag_analysis.html', tags=tags)

# Route for activity by month analysis
@app.route('/activity_by_month')
def activity_by_month():
    with Database() as db:
        months = db.fetchall("""
            SELECT 
                strftime('%Y-%m', i.opprettet_dato) AS måned,
                COUNT(DISTINCT i.innlegg_id) AS antall_innlegg,
                COUNT(DISTINCT k.kommentar_id) AS antall_kommentarer,
                COUNT(DISTINCT r.reaksjon_id) AS antall_reaksjoner,
                COUNT(DISTINCT i.bruker_id) AS aktive_brukere
            FROM INNLEGG i
            LEFT JOIN KOMMENTARER k ON strftime('%Y-%m', i.opprettet_dato) = strftime('%Y-%m', k.opprettet_dato)
            LEFT JOIN REAKSJONER r ON strftime('%Y-%m', i.opprettet_dato) = strftime('%Y-%m', r.opprettet_dato)
            GROUP BY strftime('%Y-%m', i.opprettet_dato)
            ORDER BY måned DESC
        """)
    return render_template('analytics/activity_by_month.html', months=months)
if __name__ == '__main__':
    app.run(debug=True)