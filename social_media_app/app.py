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
# Oppdater view_user ruten til å inkludere alle brukere
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
            
            # Get all users for the follow form
            all_users = db.fetchall("SELECT bruker_id, brukernavn FROM BRUKERE WHERE status = 'aktiv'")
            
            return render_template('users/view.html', user=user, posts=posts, 
                                followers=followers['count'] if followers else 0, 
                                following=following['count'] if following else 0,
                                all_users=all_users)
    flash('User not found', 'danger')
    return redirect(url_for('list_users'))

# Add this to app.py - Route for following/unfollowing users
@app.route('/users/<int:user_id>/follow', methods=['POST'])
def follow_user(user_id):
    follower_id = request.form['follower_id']  # ID til brukeren som følger
    
    if follower_id == str(user_id):
        flash('Du kan ikke følge deg selv!', 'warning')
        return redirect(url_for('view_user', user_id=user_id))
    
    try:
        with Database() as db:
            # Sjekk om relasjonen allerede eksisterer
            existing = db.fetchone("""
                SELECT * FROM FØLGER 
                WHERE følger_id = ? AND følger_bruker_id = ?
            """, (follower_id, user_id))
            
            if existing:
                # Hvis relasjonen allerede finnes, endre status (toggle)
                new_status = 'inaktiv' if existing['status'] == 'aktiv' else 'aktiv'
                db.execute("""
                    UPDATE FØLGER 
                    SET status = ?, opprettet_dato = datetime('now')
                    WHERE følge_id = ?
                """, (new_status, existing['følge_id']))
                
                if new_status == 'aktiv':
                    flash('Du følger nå denne brukeren!', 'success')
                else:
                    flash('Du følger ikke lenger denne brukeren.', 'info')
            else:
                # Opprett ny følgerelasjon
                db.execute("""
                    INSERT INTO FØLGER (følger_id, følger_bruker_id, opprettet_dato, status)
                    VALUES (?, ?, datetime('now'), 'aktiv')
                """, (follower_id, user_id))
                flash('Du følger nå denne brukeren!', 'success')
            
        return redirect(url_for('view_user', user_id=user_id))
    except Exception as e:
        flash(f'Feil ved oppdatering av følgestatus: {str(e)}', 'danger')
        return redirect(url_for('view_user', user_id=user_id))

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

        print(f"DEBUG: Innlegg ID: {post_id}")
        print(f"DEBUG: Antall kommentarer funnet: {len(comments) if comments else 0}")
        for comment in comments:
            print(f"DEBUG: Kommentar ID: {comment['kommentar_id']}, Innhold: {comment['innhold']}")
        
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

@app.route('/fix_comments', methods=['GET'])
def fix_comments():
    try:
        with Database() as db:
            # Sjekk antall eksisterende kommentarer
            existing = db.fetchone("SELECT COUNT(*) AS count FROM KOMMENTARER")
            existing_count = existing['count'] if existing else 0
            
            # Slett eksisterende kommentarer hvis nødvendig
            db.execute("DELETE FROM KOMMENTARER")
            
            # Sjekk om brukere finnes
            users = db.fetchall("SELECT bruker_id, brukernavn FROM BRUKERE")
            user_ids = [user['bruker_id'] for user in users]
            user_info = {user['bruker_id']: user['brukernavn'] for user in users}
            
            # Sjekk om innlegg finnes
            posts = db.fetchall("SELECT innlegg_id FROM INNLEGG")
            post_ids = [post['innlegg_id'] for post in posts]
            
            # Vis informasjon om tilgjengelige brukere og innlegg
            debug_info = f"<h4>Tilgjengelige brukere ({len(user_ids)}): {user_ids}</h4>"
            debug_info += f"<h4>Tilgjengelige innlegg ({len(post_ids)}): {post_ids}</h4>"
            
            # Legg inn kommentarer fra sample data
            comments_data = [
                ('Nydelig bilde! Hvor er dette tatt?', '2023-07-01 19:10:00', 1, 2, None),
                ('Ser fantastisk ut! Må prøve denne oppskriften.', '2023-07-02 13:05:00', 2, 4, None),
                ('Python er et flott språk å starte med. Prøv å lage et lite prosjekt!', '2023-07-03 10:30:00', 3, 6, None),
                ('Colosseum er et must! Og ikke glem å besøke Trastevere for god mat.', '2023-07-04 16:45:00', 4, 7, None),
                ('Hvilken treningsrutine følger du?', '2023-07-05 08:20:00', 5, 8, None),
                ('Hvilket band var det?', '2023-07-06 10:35:00', 6, 9, None),
                ('Det var i Hardanger. Takk!', '2023-07-01 20:00:00', 1, 1, 1),
                ('Jeg følger et program med fokus på styrketrening 3 ganger i uken.', '2023-07-05 09:15:00', 5, 5, 5),
                ('Kan du dele oppskriften?', '2023-07-02 14:10:00', 2, 5, 2),
                ('Arctic Monkeys. De var helt fantastiske live!', '2023-07-06 11:05:00', 6, 10, 6),
                ('Kunstutstillingen var virkelig inspirerende!', '2023-07-07 15:00:00', 7, 11, None),
                ('Jeg har lest den! En av årets beste bøker etter min mening.', '2023-07-08 21:20:00', 8, 12, None),
                ('Hvilken sci-fi film var det?', '2023-07-09 19:30:00', 9, 3, None),
                ('Gratulerer med ny jobb! Hva skal du jobbe med?', '2023-07-10 09:15:00', 10, 1, None)
            ]
            
            inserted_count = 0
            failure_details = []
            
            for comment_data in comments_data:
                content, date, post_id, user_id, parent_id = comment_data
                
                try:
                    # Sjekk om innlegg og bruker finnes
                    post_exists = post_id in post_ids
                    user_exists = user_id in user_ids
                    
                    if not post_exists:
                        failure_details.append(f"Innlegg med ID {post_id} finnes ikke")
                        continue
                        
                    if not user_exists:
                        failure_details.append(f"Bruker med ID {user_id} finnes ikke")
                        continue
                    
                    # Legg til kommentaren
                    comment_id = db.execute(
                        "INSERT INTO KOMMENTARER (innhold, opprettet_dato, innlegg_id, bruker_id, forelder_kommentar_id) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (content, date, post_id, user_id, None)  # Setter parent_id til None først
                    )
                    
                    inserted_count += 1
                    
                except Exception as e:
                    failure_details.append(f"Feil ved innsetting av '{content[:20]}...': {str(e)}")
            
            # Oppdater senere forelder-referanser om nødvendig
            
            # Sjekk antall kommentarer etter innsetting
            after = db.fetchone("SELECT COUNT(*) AS count FROM KOMMENTARER")
            after_count = after['count'] if after else 0
            
            # Forbered detaljert feilrapport
            failure_report = "<h4>Detaljer om feil:</h4><ul>"
            for detail in failure_details:
                failure_report += f"<li>{detail}</li>"
            failure_report += "</ul>"
            
            return f"""
            <h3>Kommentar-fiksen er fullført!</h3>
            <p>Før: {existing_count} kommentarer</p>
            <p>Etter: {after_count} kommentarer</p>
            <p>Forsøkt å legge til: {len(comments_data)} kommentarer</p>
            <p>Vellykket lagt til: {inserted_count} kommentarer</p>
            <p>Feilet: {len(comments_data) - inserted_count} kommentarer</p>
            
            {debug_info}
            
            {failure_report}
            
            <p><a href="/debug_comments">Se kommentaroversikt</a></p>
            <p><a href="/reset_db">Tilbakestill databasen</a></p>
            """
    except Exception as e:
        return f"Generell feil ved fiksing av kommentarer: {str(e)}"

# Legg også til en rute for å tilbakestille hele databasen
@app.route('/reset_db')
def reset_db():
    try:
        # Kjør init_db og import_sql_sample_data
        init_db()
        success = import_sql_sample_data()
        
        return f"""
        <h3>Database tilbakestilt</h3>
        <p>Status: {'Vellykket' if success else 'Feilet'}</p>
        <p><a href="/debug_comments">Se kommentaroversikt</a></p>
        <p><a href="/">Gå til forsiden</a></p>
        """
    except Exception as e:
        return f"Feil ved tilbakestilling av database: {str(e)}"
    
@app.route('/fix_comments_complete', methods=['GET'])
def fix_comments_complete():
    try:
        with Database() as db:
            # Sjekk antall eksisterende kommentarer
            existing = db.fetchone("SELECT COUNT(*) AS count FROM KOMMENTARER")
            existing_count = existing['count'] if existing else 0
            
            # Slett eksisterende kommentarer
            db.execute("DELETE FROM KOMMENTARER")
            
            # Hent alle faktiske brukere og innlegg
            users = db.fetchall("SELECT bruker_id, brukernavn FROM BRUKERE ORDER BY bruker_id")
            posts = db.fetchall("SELECT innlegg_id, innhold FROM INNLEGG ORDER BY opprettet_dato ASC")
            
            # Vis bruker-informasjon
            user_info = "<h4>Brukere i databasen:</h4><ul>"
            for user in users:
                user_info += f"<li>ID {user['bruker_id']}: {user['brukernavn']}</li>"
            user_info += "</ul>"
            
            # Opprett mappinger fra opprinnelige IDer til faktiske IDer
            post_mapping = {}
            for i, post in enumerate(posts):
                original_id = i + 1
                post_mapping[original_id] = post['innlegg_id']
            
            # Lag en mapping for brukere
            # I den opprinnelige dataen, bruker-ID 1-12 tilsvarer de første 12 brukerne i databasen
            user_mapping = {}
            for i, user in enumerate(users):
                original_id = i + 1
                user_mapping[original_id] = user['bruker_id']
            
            # Vis mappingene
            mapping_info = "<h4>Innlegg-mapping:</h4><ul>"
            for orig_id, actual_id in post_mapping.items():
                mapping_info += f"<li>Original ID {orig_id} → Faktisk ID {actual_id}</li>"
            mapping_info += "</ul>"
            
            mapping_info += "<h4>Bruker-mapping:</h4><ul>"
            for orig_id, actual_id in user_mapping.items():
                mapping_info += f"<li>Original ID {orig_id} → Faktisk ID {actual_id}</li>"
            mapping_info += "</ul>"
            
            # Opprinnelige kommentar-data
            comments_data = [
                ('Nydelig bilde! Hvor er dette tatt?', '2023-07-01 19:10:00', 1, 2, None),
                ('Ser fantastisk ut! Må prøve denne oppskriften.', '2023-07-02 13:05:00', 2, 4, None),
                ('Python er et flott språk å starte med. Prøv å lage et lite prosjekt!', '2023-07-03 10:30:00', 3, 6, None),
                ('Colosseum er et must! Og ikke glem å besøke Trastevere for god mat.', '2023-07-04 16:45:00', 4, 7, None),
                ('Hvilken treningsrutine følger du?', '2023-07-05 08:20:00', 5, 8, None),
                ('Hvilket band var det?', '2023-07-06 10:35:00', 6, 9, None),
                ('Det var i Hardanger. Takk!', '2023-07-01 20:00:00', 1, 1, 1),
                ('Jeg følger et program med fokus på styrketrening 3 ganger i uken.', '2023-07-05 09:15:00', 5, 5, 5),
                ('Kan du dele oppskriften?', '2023-07-02 14:10:00', 2, 5, 2),
                ('Arctic Monkeys. De var helt fantastiske live!', '2023-07-06 11:05:00', 6, 10, 6),
                ('Kunstutstillingen var virkelig inspirerende!', '2023-07-07 15:00:00', 7, 11, None),
                ('Jeg har lest den! En av årets beste bøker etter min mening.', '2023-07-08 21:20:00', 8, 12, None),
                ('Hvilken sci-fi film var det?', '2023-07-09 19:30:00', 9, 3, None),
                ('Gratulerer med ny jobb! Hva skal du jobbe med?', '2023-07-10 09:15:00', 10, 1, None)
            ]
            
            # Juster kommentarene til å bruke faktiske innlegg-IDer og bruker-IDer
            adjusted_comments = []
            for content, date, orig_post_id, orig_user_id, parent_comment_id in comments_data:
                actual_post_id = post_mapping.get(orig_post_id)
                actual_user_id = user_mapping.get(orig_user_id)
                
                if actual_post_id is not None and actual_user_id is not None:
                    adjusted_comments.append((content, date, actual_post_id, actual_user_id, parent_comment_id))
            
            # Legg inn første omgang med kommentarer (uten foreldre)
            inserted_comments = {}  # Original kommentar-ID til ny kommentar-ID
            inserted_count = 0
            failure_details = []
            
            for i, (content, date, post_id, user_id, _) in enumerate(adjusted_comments):
                original_comment_id = i + 1  # 1-basert kommentar-ID
                
                try:
                    # Legg til kommentar uten forelder først
                    new_comment_id = db.execute(
                        "INSERT INTO KOMMENTARER (innhold, opprettet_dato, innlegg_id, bruker_id, forelder_kommentar_id) "
                        "VALUES (?, ?, ?, ?, NULL)",
                        (content, date, post_id, user_id)
                    )
                    
                    # Lagre mapping mellom original kommentar-ID og ny kommentar-ID
                    inserted_comments[original_comment_id] = new_comment_id
                    inserted_count += 1
                    
                except Exception as e:
                    failure_details.append(f"Feil ved innsetting av kommentar {original_comment_id}: {str(e)}")
                    print(f"Feil ved innsetting: PostID={post_id}, UserID={user_id}, Error={str(e)}")
            
            # Oppdater foreldre-referanser
            parent_updates = 0
            for i, (_, _, _, _, parent_id) in enumerate(adjusted_comments):
                original_comment_id = i + 1
                
                if parent_id is not None and original_comment_id in inserted_comments:
                    if parent_id in inserted_comments:
                        try:
                            new_comment_id = inserted_comments[original_comment_id]
                            new_parent_id = inserted_comments[parent_id]
                            
                            # Oppdater forelder-referansen
                            db.execute(
                                "UPDATE KOMMENTARER SET forelder_kommentar_id = ? WHERE kommentar_id = ?",
                                (new_parent_id, new_comment_id)
                            )
                            parent_updates += 1
                            
                        except Exception as e:
                            failure_details.append(f"Feil ved oppdatering av forelder for kommentar {original_comment_id}: {str(e)}")
            
            # Sjekk antall kommentarer etter innsetting
            after = db.fetchone("SELECT COUNT(*) AS count FROM KOMMENTARER")
            after_count = after['count'] if after else 0
            
            # Forbered detaljert feilrapport
            failure_report = ""
            if failure_details:
                failure_report = "<h4>Detaljer om feil:</h4><ul>"
                for detail in failure_details:
                    failure_report += f"<li>{detail}</li>"
                failure_report += "</ul>"
            
            return f"""
            <h3>Komplett kommentar-fiks er fullført!</h3>
            <p>Før: {existing_count} kommentarer</p>
            <p>Etter: {after_count} kommentarer</p>
            <p>Forsøkt å legge til: {len(adjusted_comments)} kommentarer</p>
            <p>Vellykket lagt til: {inserted_count} kommentarer</p>
            <p>Foreldre-referanser oppdatert: {parent_updates}</p>
            
            {user_info}
            
            {mapping_info}
            
            {failure_report}
            
            <p><a href="/debug_comments">Se kommentaroversikt</a></p>
            <p><a href="/">Gå til forsiden</a></p>
            """
    except Exception as e:
        return f"Generell feil ved fiksing av kommentarer: {str(e)}"


@app.route('/debug_comments')
def debug_comments():
    with Database() as db:
        # Sjekk om kommentarer finnes i det hele tatt
        all_comments = db.fetchall("SELECT * FROM KOMMENTARER")
        comment_count = len(all_comments)
        
        # Sjekk om kommentarer er knyttet til innlegg
        comments_per_post = db.fetchall("""
            SELECT innlegg_id, COUNT(*) as comment_count 
            FROM KOMMENTARER 
            GROUP BY innlegg_id
        """)
        
        return f"Totalt antall kommentarer: {comment_count}<br>Kommentarer per innlegg: {comments_per_post}"

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
    
    # Legg til denne ruten i app.py
@app.route('/posts/<int:post_id>/react', methods=['POST'])
def add_reaction(post_id):
    bruker_id = request.form['bruker_id']
    reaksjon_type = request.form.get('reaksjon_type', 'like')
    
    try:
        with Database() as db:
            # Sjekk om innlegget eksisterer
            post = db.fetchone("SELECT * FROM INNLEGG WHERE innlegg_id = ?", (post_id,))
            if not post:
                flash('Innlegg ikke funnet', 'danger')
                return redirect(url_for('list_posts'))
                
            # Sjekk om brukeren allerede har reagert på dette innlegget
            existing_reaction = db.fetchone(
                "SELECT * FROM REAKSJONER WHERE bruker_id = ? AND innlegg_id = ?",
                (bruker_id, post_id)
            )
            
            if existing_reaction:
                # Hvis brukeren allerede har reagert, fjern reaksjonen (toggle)
                db.execute(
                    "DELETE FROM REAKSJONER WHERE reaksjon_id = ?",
                    (existing_reaction['reaksjon_id'],)
                )
                flash('Reaksjon fjernet', 'success')
            else:
                # Legg til ny reaksjon
                db.execute(
                    "INSERT INTO REAKSJONER (reaksjon_type, opprettet_dato, bruker_id, innlegg_id, kommentar_id) "
                    "VALUES (?, datetime('now'), ?, ?, NULL)",
                    (reaksjon_type, bruker_id, post_id)
                )
                flash('Reaksjon lagt til', 'success')
            
        return redirect(url_for('view_post', post_id=post_id))
    except Exception as e:
        flash(f'Feil ved håndtering av reaksjon: {str(e)}', 'danger')
        return redirect(url_for('view_post', post_id=post_id))
    

@app.route('/fix_all_relations', methods=['GET'])
def fix_all_relations():
    try:
        with Database() as db:
            # Slett eksisterende relasjoner
            db.execute("DELETE FROM INNLEGG_TAGGER")
            db.execute("DELETE FROM REAKSJONER")
            db.execute("DELETE FROM KOMMENTARER")
            
            # Hent alle faktiske brukere, innlegg og tagger
            users = db.fetchall("SELECT bruker_id, brukernavn FROM BRUKERE ORDER BY bruker_id")
            posts = db.fetchall("SELECT innlegg_id, innhold FROM INNLEGG ORDER BY opprettet_dato ASC")
            tags = db.fetchall("SELECT tag_id, navn FROM TAGGER ORDER BY tag_id")
            
            # Opprett mappinger fra opprinnelige IDer til faktiske IDer
            post_mapping = {}
            for i, post in enumerate(posts):
                original_id = i + 1  # 1-basert indeksering
                post_mapping[original_id] = post['innlegg_id']
            
            user_mapping = {}
            for i, user in enumerate(users):
                original_id = i + 1  # 1-basert indeksering
                user_mapping[original_id] = user['bruker_id']
            
            tag_mapping = {}
            for i, tag in enumerate(tags):
                original_id = i + 1  # 1-basert indeksering
                tag_mapping[original_id] = tag['tag_id']
            
            # Samle info om mappingene
            mapping_info = "<h4>Mappinger:</h4>"
            mapping_info += "<p>Innlegg: Original ID → Faktisk ID</p><ul>"
            for orig_id, actual_id in post_mapping.items():
                mapping_info += f"<li>{orig_id} → {actual_id}</li>"
            mapping_info += "</ul>"
            
            mapping_info += "<p>Brukere: Original ID → Faktisk ID</p><ul>"
            for orig_id, actual_id in user_mapping.items():
                mapping_info += f"<li>{orig_id} → {actual_id}</li>"
            mapping_info += "</ul>"
            
            mapping_info += "<p>Tagger: Original ID → Faktisk ID</p><ul>"
            for orig_id, actual_id in tag_mapping.items():
                mapping_info += f"<li>{orig_id} → {actual_id}</li>"
            mapping_info += "</ul>"
            
            # 1. Legg inn kommentarer
            comments_data = [
                ('Nydelig bilde! Hvor er dette tatt?', '2023-07-01 19:10:00', 1, 2, None),
                ('Ser fantastisk ut! Må prøve denne oppskriften.', '2023-07-02 13:05:00', 2, 4, None),
                ('Python er et flott språk å starte med. Prøv å lage et lite prosjekt!', '2023-07-03 10:30:00', 3, 6, None),
                ('Colosseum er et must! Og ikke glem å besøke Trastevere for god mat.', '2023-07-04 16:45:00', 4, 7, None),
                ('Hvilken treningsrutine følger du?', '2023-07-05 08:20:00', 5, 8, None),
                ('Hvilket band var det?', '2023-07-06 10:35:00', 6, 9, None),
                ('Det var i Hardanger. Takk!', '2023-07-01 20:00:00', 1, 1, 1),
                ('Jeg følger et program med fokus på styrketrening 3 ganger i uken.', '2023-07-05 09:15:00', 5, 5, 5),
                ('Kan du dele oppskriften?', '2023-07-02 14:10:00', 2, 5, 2),
                ('Arctic Monkeys. De var helt fantastiske live!', '2023-07-06 11:05:00', 6, 10, 6),
                ('Kunstutstillingen var virkelig inspirerende!', '2023-07-07 15:00:00', 7, 11, None),
                ('Jeg har lest den! En av årets beste bøker etter min mening.', '2023-07-08 21:20:00', 8, 12, None),
                ('Hvilken sci-fi film var det?', '2023-07-09 19:30:00', 9, 3, None),
                ('Gratulerer med ny jobb! Hva skal du jobbe med?', '2023-07-10 09:15:00', 10, 1, None)
            ]
            
            comment_mapping = {}  # For å mappe originale kommentar-IDer til nye
            comments_inserted = 0
            comments_failed = 0
            
            for i, (content, date, orig_post_id, orig_user_id, _) in enumerate(comments_data):
                original_comment_id = i + 1
                
                try:
                    actual_post_id = post_mapping.get(orig_post_id)
                    actual_user_id = user_mapping.get(orig_user_id)
                    
                    if actual_post_id and actual_user_id:
                        # Legg inn kommentar uten forelder-referanse først
                        new_comment_id = db.execute(
                            "INSERT INTO KOMMENTARER (innhold, opprettet_dato, innlegg_id, bruker_id, forelder_kommentar_id) "
                            "VALUES (?, ?, ?, ?, NULL)",
                            (content, date, actual_post_id, actual_user_id)
                        )
                        
                        comment_mapping[original_comment_id] = new_comment_id
                        comments_inserted += 1
                    else:
                        comments_failed += 1
                        print(f"Mangler mapping for Post ID {orig_post_id} eller User ID {orig_user_id}")
                except Exception as e:
                    comments_failed += 1
                    print(f"Feil ved innsetting av kommentar: {str(e)}")
            
            # Oppdater foreldre-referanser
            parent_updates = 0
            for i, (_, _, _, _, parent_id) in enumerate(comments_data):
                original_comment_id = i + 1
                
                if parent_id and parent_id in comment_mapping and original_comment_id in comment_mapping:
                    try:
                        db.execute(
                            "UPDATE KOMMENTARER SET forelder_kommentar_id = ? WHERE kommentar_id = ?",
                            (comment_mapping[parent_id], comment_mapping[original_comment_id])
                        )
                        parent_updates += 1
                    except Exception as e:
                        print(f"Feil ved oppdatering av forelder: {str(e)}")
            
            # 2. Legg inn reaksjoner
            reactions_data = [
                ('like', '2023-07-01 19:05:00', 2, 1, None),
                ('love', '2023-07-01 19:30:00', 3, 1, None),
                ('like', '2023-07-02 13:10:00', 5, 2, None),
                ('like', '2023-07-02 13:45:00', 6, 2, None),
                ('like', '2023-07-03 10:20:00', 4, 3, None),
                ('like', '2023-07-03 11:00:00', 5, 3, None),
                ('like', '2023-07-04 17:00:00', 8, 4, None),
                ('like', '2023-07-05 08:30:00', 9, 5, None),
                ('love', '2023-07-06 10:40:00', 11, 6, None),
                ('like', '2023-07-07 14:50:00', 12, 7, None),
                ('like', '2023-07-08 21:00:00', 1, 8, None),
                ('like', '2023-07-09 19:20:00', 2, 9, None),
                ('like', '2023-07-10 09:10:00', 3, 10, None),
                ('like', '2023-07-11 16:00:00', 5, 11, None),
                ('like', '2023-07-01 19:15:00', 4, None, 1),
                ('like', '2023-07-02 14:00:00', 7, None, 2)
            ]
            
            reactions_inserted = 0
            reactions_failed = 0
            
            for reaction_type, date, orig_user_id, orig_post_id, orig_comment_id in reactions_data:
                try:
                    actual_user_id = user_mapping.get(orig_user_id)
                    actual_post_id = post_mapping.get(orig_post_id) if orig_post_id else None
                    actual_comment_id = comment_mapping.get(orig_comment_id) if orig_comment_id else None
                    
                    if actual_user_id and (actual_post_id or actual_comment_id):
                        db.execute(
                            "INSERT INTO REAKSJONER (reaksjon_type, opprettet_dato, bruker_id, innlegg_id, kommentar_id) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (reaction_type, date, actual_user_id, actual_post_id, actual_comment_id)
                        )
                        reactions_inserted += 1
                    else:
                        reactions_failed += 1
                except Exception as e:
                    reactions_failed += 1
                    print(f"Feil ved innsetting av reaksjon: {str(e)}")
            
            # 3. Legg inn innlegg-tagger
            tags_data = [
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
            
            tags_inserted = 0
            tags_failed = 0
            
            for orig_post_id, orig_tag_id in tags_data:
                try:
                    actual_post_id = post_mapping.get(orig_post_id)
                    actual_tag_id = tag_mapping.get(orig_tag_id)
                    
                    if actual_post_id and actual_tag_id:
                        db.execute(
                            "INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES (?, ?)",
                            (actual_post_id, actual_tag_id)
                        )
                        tags_inserted += 1
                    else:
                        tags_failed += 1
                except Exception as e:
                    tags_failed += 1
                    print(f"Feil ved innsetting av innlegg-tag: {str(e)}")
            
            # Samle statistikk
            stats = {
                'comments': db.fetchone("SELECT COUNT(*) as count FROM KOMMENTARER")['count'],
                'reactions': db.fetchone("SELECT COUNT(*) as count FROM REAKSJONER")['count'],
                'post_tags': db.fetchone("SELECT COUNT(*) as count FROM INNLEGG_TAGGER")['count']
            }
            
            return f"""
            <h2>Alle relasjoner er fikset!</h2>
            
            <h3>Kommentarer</h3>
            <p>Lagt til: {comments_inserted} av {len(comments_data)}</p>
            <p>Feilet: {comments_failed}</p>
            <p>Foreldre-referanser oppdatert: {parent_updates}</p>
            
            <h3>Reaksjoner</h3>
            <p>Lagt til: {reactions_inserted} av {len(reactions_data)}</p>
            <p>Feilet: {reactions_failed}</p>
            
            <h3>Innlegg-tagger</h3>
            <p>Lagt til: {tags_inserted} av {len(tags_data)}</p>
            <p>Feilet: {tags_failed}</p>
            
            <h3>Database status</h3>
            <p>Antall kommentarer: {stats['comments']}</p>
            <p>Antall reaksjoner: {stats['reactions']}</p>
            <p>Antall innlegg-tagger: {stats['post_tags']}</p>
            
            {mapping_info}
            
            <p><a href="/debug_comments">Se kommentaroversikt</a></p>
            <p><a href="/">Gå til forsiden</a></p>
            """
    except Exception as e:
        return f"Generell feil ved fiksing av relasjoner: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
    