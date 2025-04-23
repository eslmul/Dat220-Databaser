from flask import Flask, render_template, request, redirect, url_for, flash, session
from db_config import Database, init_db, add_sample_data
from import_sql_sample_data import import_sql_sample_data
from werkzeug.utils import secure_filename
import uuid
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages and sessions

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB maks filstørrelse

# Opprett upload-mappen hvis den ikke finnes
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Hjelpefunksjon for å sjekke tillatte filtyper
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Hjelpefunksjon for å håndtere bildeopplasting
def handle_image_upload(file, old_filename=None):
    if file and file.filename and allowed_file(file.filename):
        # Fjern gammel fil hvis en ny lastes opp
        if old_filename and old_filename != 'default.jpg':
            old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception:
                    pass  # Ignorerer feil ved sletting av gammel fil
                
        # Generer et unikt filnavn for å unngå kollisjoner
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Lagre filen
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        return unique_filename
    
    # Returner gammel filnavn hvis ingen ny fil ble lastet opp
    return old_filename

# Modifiser CREATE - Process user creation for å støtte bildeopplasting
@app.route('/users/create', methods=['POST'])
def create_user():
    username = request.form['brukernavn']
    email = request.form['epost']
    password_hash = request.form['passord_hash']  # In a real app, you'd hash this
    bio = request.form['bio']
    birth_date = request.form['fødselsdato'] if request.form['fødselsdato'] else None
    
    # Håndter profilbilde-opplasting
    profile_image = None
    if 'profilbilde' in request.files:
        profile_image = handle_image_upload(request.files['profilbilde'])
    
    try:
        with Database() as db:
            user_id = db.execute(
                "INSERT INTO BRUKERE (brukernavn, epost, passord_hash, profilbilde, bio, fødselsdato, status) "
                "VALUES (?, ?, ?, ?, ?, ?, 'aktiv')",
                (username, email, password_hash, profile_image, bio, birth_date)
            )
        flash('User created successfully!', 'success')
        return redirect(url_for('view_user', user_id=user_id))
    except Exception as e:
        flash(f'Error creating user: {str(e)}', 'danger')
        return render_template('users/create.html')

# Modifiser UPDATE - Process user update for å støtte bildeopplasting
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
        
        # Håndter profilbilde-opplasting
        profile_image = user['profilbilde']  # Default til eksisterende bilde
        if 'profilbilde' in request.files and request.files['profilbilde'].filename:
            profile_image = handle_image_upload(request.files['profilbilde'], old_filename=profile_image)
        
        # Update user data
        db.execute(
            "UPDATE BRUKERE SET bio = ?, status = ?, profilbilde = ? WHERE bruker_id = ?",
            (bio, status, profile_image, user_id)
        )
        
    flash('User updated successfully!', 'success')
    return redirect(url_for('view_user', user_id=user_id))


# Legg til route for bildeopplasting til innlegg
@app.route('/posts/<int:post_id>/upload_image', methods=['POST'])
def upload_post_image(post_id):
    try:
        with Database() as db:
            # Sjekk om innlegget eksisterer
            post = db.fetchone("SELECT * FROM INNLEGG WHERE innlegg_id = ?", (post_id,))
            if not post:
                flash('Post not found', 'danger')
                return redirect(url_for('list_posts'))
            
            # Håndter bildeopplasting
            if 'image' in request.files:
                image_filename = handle_image_upload(request.files['image'])
                if image_filename:
                    # Legg til bildestien i innleggsinnholdet
                    updated_content = post['innhold'] + f'\n\n<img src="/static/uploads/{image_filename}" class="img-fluid rounded" alt="Post image">'
                    
                    # Oppdater innlegget
                    db.execute(
                        "UPDATE INNLEGG SET innhold = ?, oppdatert_dato = datetime('now') WHERE innlegg_id = ?",
                        (updated_content, post_id)
                    )
                    
                    flash('Image uploaded and added to post', 'success')
                else:
                    flash('Invalid file type or upload failed', 'danger')
            else:
                flash('No file selected', 'warning')
                
        return redirect(url_for('view_post', post_id=post_id))
    except Exception as e:
        flash(f'Error uploading image: {str(e)}', 'danger')
        return redirect(url_for('view_post', post_id=post_id))

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

def initialize_database():
    init_db()
    
    # Sjekk antall brukere, og hvis det er færre enn 10, legg til testdata
    with Database() as db:
        user_count = db.fetchone("SELECT COUNT(*) as count FROM BRUKERE")
        if not user_count or user_count['count'] < 10:
            try:
                print("Legger til testdata...")
                # 1. Sjekk sti til SQL-filen
                sql_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'MySQL', 'social_media_sample_data.sql')
                
                # Hvis filen ikke finnes på den forventede stien, prøv alternativer
                if not os.path.exists(sql_file_path):
                    alternative_paths = [
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MySQL', 'social_media_sample_data.sql'),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'social_media_sample_data.sql'),
                        'MySQL/social_media_sample_data.sql',
                        'social_media_sample_data.sql'
                    ]
                    
                    for alt_path in alternative_paths:
                        if os.path.exists(alt_path):
                            sql_file_path = alt_path
                            print(f"Fant SQL-fil på: {alt_path}")
                            break
                
                # 2. Les og kjør SQL-kommandoene direkte hvis filen finnes
                if os.path.exists(sql_file_path):
                    print(f"Importerer data fra {sql_file_path}...")
                    with open(sql_file_path, 'r', encoding='utf-8') as f:
                        sql_script = f.read()
                    
                    # Fjern kommentarer og tom plass
                    import re
                    sql_script = re.sub(r'--.*?\n', '\n', sql_script)
                    
                    # Del opp i statements basert på semikolon
                    statements = []
                    current_statement = ""
                    
                    for line in sql_script.split('\n'):
                        line = line.strip()
                        if not line or line.startswith('--'):
                            continue
                            
                        current_statement += line + " "
                        
                        if line.endswith(';'):
                            statements.append(current_statement.strip())
                            current_statement = ""
                    
                    # Filtrer ut bare INSERT-statements og kjør dem
                    insert_statements = [stmt for stmt in statements if stmt.upper().startswith('INSERT')]
                    
                    # Slå av foreign key sjekker midlertidig hvis det er SET FOREIGN_KEY_CHECKS = 0 i filen
                    db.execute("PRAGMA foreign_keys = OFF")
                    
                    for stmt in insert_statements:
                        try:
                            # Erstatt MySQL-spesifikk syntaks
                            stmt = stmt.replace('NOW()', 'CURRENT_TIMESTAMP')
                            db.execute(stmt)
                        except Exception as e:
                            print(f"Feil ved utføring av SQL: {e}")
                            print(f"Statement: {stmt}")
                    
                    # Slå på foreign key sjekker igjen
                    db.execute("PRAGMA foreign_keys = ON")
                    print("SQL-import fullført!")
                else:
                    print("Kunne ikke finne SQL-filen, prøver add_sample_data() i stedet...")
                    add_sample_data()
            except Exception as e:
                print(f"Feil ved initialisering av testdata: {e}")
                print("Prøver å legge til enkle testdata...")
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
# Duplicate function removed to resolve redefinition error.

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
# Duplicate function removed to resolve redefinition error.

# DELETE - Delete user
@app.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    with Database() as db:
        db.execute("DELETE FROM BRUKERE WHERE bruker_id = ?", (user_id,))
    flash('User deleted successfully!', 'success')
    return redirect(url_for('list_users'))


@app.route('/posts')
def list_posts():
    try:
        with Database() as db:
            # Get all posts with user info
            posts = db.fetchall("""
                SELECT i.*, b.brukernavn 
                FROM INNLEGG i 
                JOIN BRUKERE b ON i.bruker_id = b.bruker_id 
                ORDER BY i.opprettet_dato DESC
            """)
            
            # Format date fields properly
            formatted_posts = []
            for post in posts:
                post_dict = dict(post)
                
                # Ensure dates are properly formatted as datetime objects
                for date_field in ['opprettet_dato', 'oppdatert_dato']:
                    if date_field in post_dict and post_dict[date_field]:
                        try:
                            if isinstance(post_dict[date_field], str):
                                if 'T' in post_dict[date_field]:  # ISO format
                                    post_dict[date_field] = datetime.fromisoformat(post_dict[date_field].replace('Z', '+00:00'))
                                else:  # SQLite default format
                                    post_dict[date_field] = datetime.strptime(post_dict[date_field], '%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            try:
                                # Try date-only format
                                post_dict[date_field] = datetime.strptime(post_dict[date_field], '%Y-%m-%d')
                            except (ValueError, TypeError):
                                # If all parsing fails, provide a default datetime to avoid template errors
                                post_dict[date_field] = datetime.now()
                
                formatted_posts.append(post_dict)
            
            return render_template('posts/list.html', posts=formatted_posts)
            
    except Exception as e:
        flash(f'Error fetching posts: {str(e)}', 'danger')
        return render_template('posts/list.html', posts=[])
    
@app.route('/reset_posts', methods=['GET'])
def reset_posts():
    try:
        with Database() as db:
            # First delete all existing posts relationships
            db.execute("DELETE FROM INNLEGG_TAGGER")
            db.execute("DELETE FROM KOMMENTARER")
            db.execute("DELETE FROM REAKSJONER WHERE innlegg_id IS NOT NULL")
            db.execute("DELETE FROM INNLEGG")
            
            # Now insert the correct posts from the sample data
            # These mappings match the original data from social_media_sample_data.sql
            post_data = [
                ('Fantastisk solnedgang fra fjellturen i dag! #natur #fjelltur', '2023-07-01 18:45:00', 'offentlig', 'johansen94'),
                ('Ny oppskrift på hjemmelaget pasta med sesongbaserte råvarer. Deilig sommermat!', '2023-07-02 12:30:00', 'offentlig', 'jensten'),
                ('Har nettopp lært meg grunnleggende Python-programmering. Fascinerende!', '2023-07-03 09:15:00', 'offentlig', 'olekristian'),
                ('På vei til Roma! Noen tips til hva jeg bør se?', '2023-07-04 16:20:00', 'offentlig', 'linelise'),
                ('Min nye treningsrutine har gitt gode resultater. Deler gjerne erfaringer.', '2023-07-05 07:45:00', 'offentlig', 'pernillen'),
                ('Var på konsert med favorittbandet mitt i går. Helt utrolig opplevelse!', '2023-07-06 10:10:00', 'offentlig', 'torhild'),
                ('Besøkte en fascinerende kunstutstilling i helgen. Anbefales!', '2023-07-07 14:25:00', 'offentlig', 'karianne'),
                ('Har nettopp lest en fantastisk roman. Noen andre som har lest "Havet" av Jon Sorensen?', '2023-07-08 20:30:00', 'offentlig', 'mariaberg'),
                ('Så den nye sci-fi filmen i går. Imponerende effekter!', '2023-07-09 19:05:00', 'offentlig', 'magnush'),
                ('Første dag i ny jobb! Spent på hva framtiden bringer.', '2023-07-10 08:50:00', 'offentlig', 'martingm'),
                ('Familietur til hytta. Barna koser seg med fiske og bading.', '2023-07-11 15:40:00', 'venner', 'annesofi'),
                ('Tenker på å ta et nytt kurs i markedsføring. Noen anbefalinger?', '2023-07-12 11:15:00', 'offentlig', 'pernillen'),
                ('Tester ut nytt kamera. Her er noen av de første bildene.', '2023-07-13 13:20:00', 'offentlig', 'johansen94'),
                ('Endelig ferdig med eksamen! Nå venter sommerferie.', '2023-07-14 16:55:00', 'offentlig', 'anderskr')
            ]
            
            # Insert posts with correct user IDs
            for content, date, visibility, username in post_data:
                # Find the user ID for this username
                user = db.fetchone("SELECT bruker_id FROM BRUKERE WHERE brukernavn = ?", (username,))
                if user:
                    db.execute(
                        "INSERT INTO INNLEGG (innhold, opprettet_dato, synlighet, bruker_id) VALUES (?, ?, ?, ?)",
                        (content, date, visibility, user['bruker_id'])
                    )
            
            # Recreate tag associations
            tag_associations = [
                (1, 1),  # natur
                (2, 2),  # mat
                (3, 3),  # teknologi
                (4, 4),  # reise
                (5, 5),  # trening
                (6, 6),  # musikk
                (7, 7),  # kunst
                (8, 8),  # litteratur
                (9, 9),  # film
                (10, 11), # jobb
                (11, 12), # familie
                (12, 10), # utdanning
                (13, 1),  # natur (for kameratestbilde)
                (13, 7),  # kunst (for kameratestbilde)
                (14, 10)  # utdanning (for eksamen-innlegget)
            ]
            
            for post_id, tag_id in tag_associations:
                db.execute("INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES (?, ?)", (post_id, tag_id))
                
            flash('Posts have been reset to original sample data!', 'success')
            return redirect(url_for('list_posts'))
            
    except Exception as e:
        flash(f'Error resetting posts: {str(e)}', 'danger')
        return redirect(url_for('list_posts'))

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
            WHERE k.innlegg_id = ? AND k.forelder_kommentar_id IS NULL
            ORDER BY k.opprettet_dato ASC
        """, (post_id,))
        comments = [format_date_fields(comment, ['opprettet_dato']) for comment in comments]
        
        # Get replies for each comment
        for comment in comments:
            replies = db.fetchall("""
                SELECT k.*, b.brukernavn, b.profilbilde
                FROM KOMMENTARER k
                JOIN BRUKERE b ON k.bruker_id = b.bruker_id
                WHERE k.forelder_kommentar_id = ?
                ORDER BY k.opprettet_dato ASC
            """, (comment['kommentar_id'],))
            comment['replies'] = [format_date_fields(reply, ['opprettet_dato']) for reply in replies]
        
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
        
        # Get all users for the comment form
        users = db.fetchall("""
            SELECT bruker_id, brukernavn FROM BRUKERE
            WHERE status = 'aktiv'
            ORDER BY brukernavn
        """)
        
        return render_template('posts/view.html', post=post, comments=comments, 
                               tags=tags, reactions=reactions, users=users)

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
    new_tags = request.form.get('new_tags', '')  # Get new tags string
    
    try:
        with Database() as db:
            # Insert post
            post_id = db.execute(
                "INSERT INTO INNLEGG (innhold, opprettet_dato, synlighet, bruker_id) "
                "VALUES (?, datetime('now'), ?, ?)",
                (content, visibility, user_id)
            )
            
            # Process existing tags if any selected
            for tag_id in tag_ids:
                db.execute(
                    "INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES (?, ?)",
                    (post_id, tag_id)
                )
            
            # Process new tags if any provided
            if new_tags:
                # Split by comma and strip whitespace
                tag_names = [tag.strip() for tag in new_tags.split(',') if tag.strip()]
                
                for tag_name in tag_names:
                    # Check if tag already exists
                    existing_tag = db.fetchone(
                        "SELECT tag_id FROM TAGGER WHERE navn = ?",
                        (tag_name,)
                    )
                    
                    if existing_tag:
                        # Use existing tag if it exists
                        tag_id = existing_tag['tag_id']
                    else:
                        # Create new tag if it doesn't exist
                        tag_id = db.execute(
                            "INSERT INTO TAGGER (navn, beskrivelse) VALUES (?, ?)",
                            (tag_name, f"Tag opprettet for innlegg {post_id}")
                        )
                    
                    # Link tag to post
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
    new_tags = request.form.get('new_tags', '')  # Get new tags string
    
    try:
        with Database() as db:
            # Update post
            db.execute(
                "UPDATE INNLEGG SET innhold = ?, synlighet = ?, oppdatert_dato = datetime('now') WHERE innlegg_id = ?",
                (content, visibility, post_id)
            )
            
            # Delete all existing tag associations
            db.execute("DELETE FROM INNLEGG_TAGGER WHERE innlegg_id = ?", (post_id,))
            
            # Insert existing tag associations
            for tag_id in tag_ids:
                db.execute(
                    "INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES (?, ?)",
                    (post_id, tag_id)
                )
            
            # Process new tags if any provided
            if new_tags:
                # Split by comma and strip whitespace
                tag_names = [tag.strip() for tag in new_tags.split(',') if tag.strip()]
                
                for tag_name in tag_names:
                    # Check if tag already exists
                    existing_tag = db.fetchone(
                        "SELECT tag_id FROM TAGGER WHERE navn = ?",
                        (tag_name,)
                    )
                    
                    if existing_tag:
                        # Use existing tag if it exists
                        tag_id = existing_tag['tag_id']
                    else:
                        # Create new tag if it doesn't exist
                        tag_id = db.execute(
                            "INSERT INTO TAGGER (navn, beskrivelse) VALUES (?, ?)",
                            (tag_name, f"Tag opprettet for innlegg {post_id}")
                        )
                    
                    # Link tag to post
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

# Add a new comment to a post
@app.route('/posts/<int:post_id>/comments/add', methods=['POST'])
def add_comment(post_id):
    bruker_id = request.form['bruker_id']
    innhold = request.form['innhold']
    
    try:
        with Database() as db:
            # Check if post exists
            post = db.fetchone("SELECT * FROM INNLEGG WHERE innlegg_id = ?", (post_id,))
            if not post:
                flash('Innlegg ikke funnet', 'danger')
                return redirect(url_for('list_posts'))
                
            # Insert comment
            db.execute(
                "INSERT INTO KOMMENTARER (innhold, opprettet_dato, innlegg_id, bruker_id, forelder_kommentar_id) "
                "VALUES (?, datetime('now'), ?, ?, NULL)",
                (innhold, post_id, bruker_id)
            )
            
        flash('Kommentar lagt til', 'success')
    except Exception as e:
        flash(f'Feil ved oppretting av kommentar: {str(e)}', 'danger')
    
    return redirect(url_for('view_post', post_id=post_id))

# Add a reply to a comment
@app.route('/posts/<int:post_id>/comments/<int:parent_id>/reply', methods=['POST'])
def add_reply(post_id, parent_id):
    bruker_id = request.form['bruker_id']
    innhold = request.form['innhold']
    
    try:
        with Database() as db:
            # Check if parent comment exists
            parent_comment = db.fetchone(
                "SELECT * FROM KOMMENTARER WHERE kommentar_id = ? AND innlegg_id = ?", 
                (parent_id, post_id)
            )
            
            if not parent_comment:
                flash('Opprinnelig kommentar ikke funnet', 'danger')
                return redirect(url_for('view_post', post_id=post_id))
                
            # Insert reply
            db.execute(
                "INSERT INTO KOMMENTARER (innhold, opprettet_dato, innlegg_id, bruker_id, forelder_kommentar_id) "
                "VALUES (?, datetime('now'), ?, ?, ?)",
                (innhold, post_id, bruker_id, parent_id)
            )
            
        flash('Svar lagt til', 'success')
    except Exception as e:
        flash(f'Feil ved oppretting av svar: {str(e)}', 'danger')
    
    return redirect(url_for('view_post', post_id=post_id))

# Delete a comment (or reply)
@app.route('/comments/<int:comment_id>/delete/<int:post_id>', methods=['POST'])
def delete_comment(comment_id, post_id):
    try:
        with Database() as db:
            # Check if comment exists
            comment = db.fetchone("SELECT * FROM KOMMENTARER WHERE kommentar_id = ?", (comment_id,))
            if not comment:
                flash('Kommentar ikke funnet', 'danger')
                return redirect(url_for('view_post', post_id=post_id))
                
            # Also delete any child comments (replies)
            db.execute("DELETE FROM KOMMENTARER WHERE forelder_kommentar_id = ?", (comment_id,))
            
            # Delete the comment itself
            db.execute("DELETE FROM KOMMENTARER WHERE kommentar_id = ?", (comment_id,))
            
        flash('Kommentar slettet', 'success')
    except Exception as e:
        flash(f'Feil ved sletting av kommentar: {str(e)}', 'danger')
    
    return redirect(url_for('view_post', post_id=post_id))

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

# Route for tag management
@app.route('/tags')
def manage_tags():
    with Database() as db:
        # Get all tags with count of posts using each tag
        tags = db.fetchall("""
            SELECT 
                t.tag_id, 
                t.navn, 
                t.beskrivelse,
                COUNT(it.innlegg_id) AS post_count
            FROM TAGGER t
            LEFT JOIN INNLEGG_TAGGER it ON t.tag_id = it.tag_id
            GROUP BY t.tag_id
            ORDER BY t.navn
        """)
    return render_template('tags/manage.html', tags=tags)

# CREATE - Process tag creation
@app.route('/tags/create', methods=['POST'])
def create_tag():
    navn = request.form['navn']
    beskrivelse = request.form['beskrivelse']
    
    try:
        with Database() as db:
            # Check if tag already exists
            existing_tag = db.fetchone(
                "SELECT tag_id FROM TAGGER WHERE navn = ?",
                (navn,)
            )
            
            if existing_tag:
                flash(f'En tagg med navnet "{navn}" finnes allerede.', 'warning')
                return redirect(url_for('manage_tags'))
                
            # Insert new tag
            db.execute(
                "INSERT INTO TAGGER (navn, beskrivelse) VALUES (?, ?)",
                (navn, beskrivelse)
            )
            
        flash(f'Taggen "{navn}" ble opprettet.', 'success')
    except Exception as e:
        flash(f'Feil ved oppretting av tagg: {str(e)}', 'danger')
    
    return redirect(url_for('manage_tags'))

# UPDATE - Process tag update
@app.route('/tags/<int:tag_id>/edit', methods=['POST'])
def edit_tag(tag_id):
    navn = request.form['navn']
    beskrivelse = request.form['beskrivelse']
    
    try:
        with Database() as db:
            # Check if tag exists
            tag = db.fetchone("SELECT * FROM TAGGER WHERE tag_id = ?", (tag_id,))
            if not tag:
                flash('Taggen ble ikke funnet.', 'danger')
                return redirect(url_for('manage_tags'))
            
            # Check if new name already exists (but skip if it's the same tag)
            existing_tag = db.fetchone(
                "SELECT tag_id FROM TAGGER WHERE navn = ? AND tag_id != ?",
                (navn, tag_id)
            )
            
            if existing_tag:
                flash(f'En tagg med navnet "{navn}" finnes allerede.', 'warning')
                return redirect(url_for('manage_tags'))
                
            # Update tag
            db.execute(
                "UPDATE TAGGER SET navn = ?, beskrivelse = ? WHERE tag_id = ?",
                (navn, beskrivelse, tag_id)
            )
            
        flash(f'Taggen "{navn}" ble oppdatert.', 'success')
    except Exception as e:
        flash(f'Feil ved oppdatering av tagg: {str(e)}', 'danger')
    
    return redirect(url_for('manage_tags'))

# DELETE - Process tag deletion
@app.route('/tags/<int:tag_id>/delete', methods=['POST'])
def delete_tag(tag_id):
    try:
        with Database() as db:
            # Get tag info for feedback message
            tag = db.fetchone("SELECT * FROM TAGGER WHERE tag_id = ?", (tag_id,))
            if not tag:
                flash('Taggen ble ikke funnet.', 'danger')
                return redirect(url_for('manage_tags'))
            
            # Get post count for this tag (for log purposes)
            post_count = db.fetchone(
                "SELECT COUNT(*) as count FROM INNLEGG_TAGGER WHERE tag_id = ?", 
                (tag_id,)
            )
            
            # Remove tag associations from posts
            db.execute("DELETE FROM INNLEGG_TAGGER WHERE tag_id = ?", (tag_id,))
            
            # Delete the tag itself
            db.execute("DELETE FROM TAGGER WHERE tag_id = ?", (tag_id,))
            
            removed_from = post_count['count'] if post_count else 0
            
            if removed_from > 0:
                flash(f'Taggen "{tag["navn"]}" ble slettet og fjernet fra {removed_from} innlegg.', 'success')
            else:
                flash(f'Taggen "{tag["navn"]}" ble slettet.', 'success')
                
    except Exception as e:
        flash(f'Feil ved sletting av tagg: {str(e)}', 'danger')
    
    return redirect(url_for('manage_tags'))



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

@app.route('/import_sample_data', methods=['GET'])
def import_sample_data_endpoint():
    try:
        success = import_sql_sample_data()
        if success:
            flash('Testdata er importert!', 'success')
        else:
            flash('Kunne ikke importere testdata.', 'danger')
    except Exception as e:
        flash(f'Feil ved import av testdata: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/debug_db_stats')
def debug_db_stats():
    with Database() as db:
        stats = {
            'users': db.fetchone("SELECT COUNT(*) as count FROM BRUKERE")['count'],
            'posts': db.fetchone("SELECT COUNT(*) as count FROM INNLEGG")['count'],
            'comments': db.fetchone("SELECT COUNT(*) as count FROM KOMMENTARER")['count'],
            'tags': db.fetchone("SELECT COUNT(*) as count FROM TAGGER")['count'],
            'post_tags': db.fetchone("SELECT COUNT(*) as count FROM INNLEGG_TAGGER")['count'],
            'reactions': db.fetchone("SELECT COUNT(*) as count FROM REAKSJONER")['count'],
            'follows': db.fetchone("SELECT COUNT(*) as count FROM FØLGER")['count'],
            'messages': db.fetchone("SELECT COUNT(*) as count FROM MELDINGER")['count']
        }
        
        # Also check a specific post (e.g., post ID 1)
        post_id = 1
        post_stats = {
            'comments': db.fetchone("SELECT COUNT(*) as count FROM KOMMENTARER WHERE innlegg_id = ?", (post_id,))['count'],
            'tags': db.fetchone("SELECT COUNT(*) as count FROM INNLEGG_TAGGER WHERE innlegg_id = ?", (post_id,))['count'],
            'reactions': db.fetchone("SELECT COUNT(*) as count FROM REAKSJONER WHERE innlegg_id = ?", (post_id,))['count']
        }
        
        return render_template('debug/db_stats.html', stats=stats, post_stats=post_stats, post_id=post_id)
    

if __name__ == '__main__':
    app.run(debug=True)
    