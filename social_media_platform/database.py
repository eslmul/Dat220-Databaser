import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    """Connect to the database if not already connected."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    """Close the database connection if it exists."""
    db = g.pop('db', None)
    
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with schema."""
    db = get_db()
    
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

def insert_sample_data():
    """Insert sample data into the database."""
    db = get_db()
    
    # Insert sample users
    users = [
        ('johansen94', 'erik.johansen@example.com', 'hash1234567890', 'profil1.jpg', 'Fotograf og friluftsentusiast fra Bergen.', '2023-01-15', '1994-05-20', 'aktiv'),
        ('mariaberg', 'maria.berg@example.com', 'hash2345678901', 'profil2.jpg', 'Journalist og bokelsker.', '2023-02-10', '1990-08-12', 'aktiv'),
        ('olekristian', 'ole.kristian@example.com', 'hash3456789012', 'profil3.jpg', 'Programmerer og teknologientusiast.', '2023-01-05', '1992-11-30', 'aktiv'),
        ('annesofi', 'anne.sofi@example.com', 'hash4567890123', 'profil4.jpg', 'Lærer og hobbybaker fra Trondheim.', '2023-03-20', '1988-07-15', 'aktiv'),
        ('pernillen', 'pernille.n@example.com', 'hash5678901234', 'profil5.jpg', 'Digital markedsfører og yogainstruktør.', '2023-02-28', '1995-04-05', 'aktiv'),
        ('magnush', 'magnus.h@example.com', 'hash6789012345', 'profil6.jpg', 'Ingeniør og fotballentusiast.', '2023-04-10', '1991-09-25', 'aktiv'),
        ('karianne', 'karianne@example.com', 'hash7890123456', 'profil7.jpg', 'Grafisk designer med passion for kunst.', '2023-03-15', '1993-12-08', 'aktiv'),
        ('anderskr', 'anders.kr@example.com', 'hash8901234567', 'profil8.jpg', 'Historiestudent og frivillig.', '2023-05-05', '1997-06-18', 'aktiv'),
        ('linelise', 'lin.elise@example.com', 'hash9012345678', 'profil9.jpg', 'Sykepleier og reiseglad.', '2023-04-20', '1989-03-22', 'aktiv'),
        ('torhild', 'tor.hild@example.com', 'hash0123456789', 'profil10.jpg', 'Musiker og vinterbader.', '2023-05-25', '1990-10-14', 'aktiv'),
        ('martingm', 'martin.gm@example.com', 'hash1122334455', 'profil11.jpg', 'Arkitekt med interesse for bærekraft.', '2023-06-01', '1986-02-28', 'aktiv'),
        ('jensten', 'jens.ten@example.com', 'hash6677889900', 'profil12.jpg', 'Kokk og matblogger.', '2023-06-15', '1994-08-05', 'aktiv')
    ]
    
    for user in users:
        db.execute(
            'INSERT INTO BRUKERE (brukernavn, epost, passord_hash, profilbilde, bio, registrerings_dato, fødselsdato, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            user
        )
    
    # Insert sample tags
    tags = [
        ('natur', 'Bilder og innlegg om naturen'),
        ('mat', 'Matoppskrifter og matopplevelser'),
        ('teknologi', 'Alt om teknologi og digitale trender'),
        ('reise', 'Reiseopplevelser og reisetips'),
        ('trening', 'Treningsrutiner og fitness'),
        ('musikk', 'Musikkanbefalinger og konsertopplevelser'),
        ('kunst', 'Kunst og kreative uttrykk'),
        ('litteratur', 'Bøker og leseopplevelser'),
        ('film', 'Filmanmeldelser og filmanbefalinger'),
        ('utdanning', 'Temaer relatert til skole og læring'),
        ('jobb', 'Arbeidslivet og karrieretips'),
        ('familie', 'Familie og hverdagsliv')
    ]
    
    for tag in tags:
        db.execute(
            'INSERT INTO TAGGER (navn, beskrivelse) VALUES (?, ?)',
            tag
        )
    
    # Insert sample posts
    posts = [
        ('Fantastisk solnedgang fra fjellturen i dag! #natur #fjelltur', '2023-07-01 18:45:00', 'offentlig', 1),
        ('Ny oppskrift på hjemmelaget pasta med sesongbaserte råvarer. Deilig sommermat!', '2023-07-02 12:30:00', 'offentlig', 12),
        ('Har nettopp lært meg grunnleggende Python-programmering. Fascinerende!', '2023-07-03 09:15:00', 'offentlig', 3),
        ('På vei til Roma! Noen tips til hva jeg bør se?', '2023-07-04 16:20:00', 'offentlig', 9),
        ('Min nye treningsrutine har gitt gode resultater. Deler gjerne erfaringer.', '2023-07-05 07:45:00', 'offentlig', 5),
        ('Var på konsert med favorittbandet mitt i går. Helt utrolig opplevelse!', '2023-07-06 10:10:00', 'offentlig', 10),
        ('Besøkte en fascinerende kunstutstilling i helgen. Anbefales!', '2023-07-07 14:25:00', 'offentlig', 7),
        ('Har nettopp lest en fantastisk roman. Noen andre som har lest "Havet" av Jon Sorensen?', '2023-07-08 20:30:00', 'offentlig', 2),
        ('Så den nye sci-fi filmen i går. Imponerende effekter!', '2023-07-09 19:05:00', 'offentlig', 6),
        ('Første dag i ny jobb! Spent på hva framtiden bringer.', '2023-07-10 08:50:00', 'offentlig', 11)
    ]
    
    for post in posts:
        db.execute(
            'INSERT INTO INNLEGG (innhold, opprettet_dato, synlighet, bruker_id) VALUES (?, ?, ?, ?)',
            post
        )
    
    # Insert post tags relationships
    post_tags = [
        (1, 1),  # Post 1, Tag 'natur'
        (2, 2),  # Post 2, Tag 'mat'
        (3, 3),  # Post 3, Tag 'teknologi'
        (4, 4),  # Post 4, Tag 'reise'
        (5, 5),  # Post 5, Tag 'trening'
        (6, 6),  # Post 6, Tag 'musikk'
        (7, 7),  # Post 7, Tag 'kunst'
        (8, 8),  # Post 8, Tag 'litteratur'
        (9, 9),  # Post 9, Tag 'film'
        (10, 11)  # Post 10, Tag 'jobb'
    ]
    
    for post_tag in post_tags:
        db.execute(
            'INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES (?, ?)',
            post_tag
        )
    
    # Insert sample comments
    comments = [
        ('Nydelig bilde! Hvor er dette tatt?', '2023-07-01 19:10:00', 1, 2, None),
        ('Ser fantastisk ut! Må prøve denne oppskriften.', '2023-07-02 13:05:00', 2, 4, None),
        ('Python er et flott språk å starte med. Prøv å lage et lite prosjekt!', '2023-07-03 10:30:00', 3, 6, None),
        ('Colosseum er et must! Og ikke glem å besøke Trastevere for god mat.', '2023-07-04 16:45:00', 4, 7, None),
        ('Hvilken treningsrutine følger du?', '2023-07-05 08:20:00', 5, 8, None),
        ('Hvilket band var det?', '2023-07-06 10:35:00', 6, 9, None),
        ('Det var i Hardanger. Takk!', '2023-07-01 20:00:00', 1, 1, 1),
        ('Jeg følger et program med fokus på styrketrening 3 ganger i uken.', '2023-07-05 09:15:00', 5, 5, 5)
    ]
    
    for comment in comments:
        db.execute(
            'INSERT INTO KOMMENTARER (innhold, opprettet_dato, innlegg_id, bruker_id, forelder_kommentar_id) VALUES (?, ?, ?, ?, ?)',
            comment
        )
    
    # Insert sample reactions
    reactions = [
        ('like', '2023-07-01 19:05:00', 2, 1, None),
        ('love', '2023-07-01 19:30:00', 3, 1, None),
        ('like', '2023-07-02 13:10:00', 5, 2, None),
        ('like', '2023-07-03 10:20:00', 4, 3, None),
        ('like', '2023-07-04 17:00:00', 8, 4, None),
        ('like', '2023-07-05 08:30:00', 9, 5, None),
        ('love', '2023-07-06 10:40:00', 11, 6, None),
        ('like', '2023-07-01 19:15:00', 4, None, 1)
    ]
    
    for reaction in reactions:
        db.execute(
            'INSERT INTO REAKSJONER (reaksjon_type, opprettet_dato, bruker_id, innlegg_id, kommentar_id) VALUES (?, ?, ?, ?, ?)',
            reaction
        )
    
    db.commit()

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

@click.command('seed-db')
@with_appcontext
def seed_db_command():
    """Seed the database with sample data."""
    insert_sample_data()
    click.echo('Database seeded with sample data.')

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)