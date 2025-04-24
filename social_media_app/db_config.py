import sqlite3
import os

# Ensure the instance folder exists
if not os.path.exists('instance'):
    os.makedirs('instance')

DB_PATH = 'instance/social_media.db'

class Database:
    def __init__(self):
        try:
            self.conn = sqlite3.connect(DB_PATH)
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Configure SQLite to return dictionaries instead of tuples
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            print("Database connection successful")
        except Exception as e:
            print(f"Error connecting to SQLite database: {e}")
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        if self.conn:
            self.conn.close()
            
    def query(self, sql, params=None):
        self.cursor.execute(sql, params or ())
        return self.cursor
        
    def fetchall(self, sql, params=None):
        self.cursor.execute(sql, params or ())
        return self.cursor.fetchall()
        
    def fetchone(self, sql, params=None):
        self.cursor.execute(sql, params or ())
        return self.cursor.fetchone()
        
    def execute(self, sql, params=None):
        self.cursor.execute(sql, params or ())
        self.conn.commit()
        return self.cursor.lastrowid

# Function to initialize the database schema
def init_db():
    with Database() as db:
        # Create BRUKERE (Users) table
        db.execute('''
        CREATE TABLE IF NOT EXISTS BRUKERE (
            bruker_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brukernavn TEXT NOT NULL UNIQUE,
            epost TEXT NOT NULL UNIQUE,
            passord_hash TEXT NOT NULL,
            profilbilde TEXT,
            bio TEXT,
            registrerings_dato DATE NOT NULL DEFAULT CURRENT_DATE,
            fødselsdato DATE,
            status TEXT DEFAULT 'aktiv'
        )
        ''')
        
        # Create INNLEGG (Posts) table
        db.execute('''
        CREATE TABLE IF NOT EXISTS INNLEGG (
            innlegg_id INTEGER PRIMARY KEY AUTOINCREMENT,
            innhold TEXT NOT NULL,
            opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            oppdatert_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
            synlighet TEXT NOT NULL DEFAULT 'offentlig',
            bruker_id INTEGER NOT NULL,
            FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE
        )
        ''')
        
        # Create KOMMENTARER (Comments) table
        db.execute('''
        CREATE TABLE IF NOT EXISTS KOMMENTARER (
            kommentar_id INTEGER PRIMARY KEY AUTOINCREMENT,
            innhold TEXT NOT NULL,
            opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            innlegg_id INTEGER NOT NULL,
            bruker_id INTEGER NOT NULL,
            forelder_kommentar_id INTEGER,
            FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
            FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
            FOREIGN KEY (forelder_kommentar_id) REFERENCES KOMMENTARER(kommentar_id) ON DELETE SET NULL
        )
        ''')
        
        # Create REAKSJONER (Reactions) table
        db.execute('''
        CREATE TABLE IF NOT EXISTS REAKSJONER (
            reaksjon_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reaksjon_type TEXT NOT NULL,
            opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            bruker_id INTEGER NOT NULL,
            innlegg_id INTEGER,
            kommentar_id INTEGER,
            FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
            FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
            FOREIGN KEY (kommentar_id) REFERENCES KOMMENTARER(kommentar_id) ON DELETE CASCADE,
            CHECK ((innlegg_id IS NOT NULL AND kommentar_id IS NULL) OR
                  (innlegg_id IS NULL AND kommentar_id IS NOT NULL))
        )
        ''')
        
        # Create FØLGER (Follows) table
        db.execute('''
        CREATE TABLE IF NOT EXISTS FØLGER (
            følge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            følger_id INTEGER NOT NULL,
            følger_bruker_id INTEGER NOT NULL,
            opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'aktiv',
            FOREIGN KEY (følger_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
            FOREIGN KEY (følger_bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
            CHECK (følger_id != følger_bruker_id),
            UNIQUE (følger_id, følger_bruker_id)
        )
        ''')
        

        
        # Create TAGGER (Tags) table
        db.execute('''
        CREATE TABLE IF NOT EXISTS TAGGER (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            navn TEXT NOT NULL UNIQUE,
            beskrivelse TEXT
        )
        ''')
        
        # Create INNLEGG_TAGGER (Post-Tags) junction table
        db.execute('''
        CREATE TABLE IF NOT EXISTS INNLEGG_TAGGER (
            innlegg_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (innlegg_id, tag_id),
            FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES TAGGER(tag_id) ON DELETE CASCADE
        )
        ''')
        
        print("Database schema initialized successfully")

# Function to add sample data
def add_sample_data():
    with Database() as db:
        # Check if data already exists
        user_count = db.fetchone("SELECT COUNT(*) as count FROM BRUKERE")
        if user_count and user_count['count'] > 0:
            print("Sample data already exists")
            return
            
        # Add sample users
        db.execute('''
        INSERT INTO BRUKERE (brukernavn, epost, passord_hash, bio, registrerings_dato, fødselsdato, status)
        VALUES 
        ('johansen94', 'erik.johansen@example.com', 'hash1234567890', 'Fotograf og friluftsentusiast fra Bergen.', '2023-01-15', '1994-05-20', 'aktiv'),
        ('mariaberg', 'maria.berg@example.com', 'hash2345678901', 'Journalist og bokelsker.', '2023-02-10', '1990-08-12', 'aktiv'),
        ('olekristian', 'ole.kristian@example.com', 'hash3456789012', 'Programmerer og teknologientusiast.', '2023-01-05', '1992-11-30', 'aktiv')
        ''')
        
        # Add sample tags
        db.execute('''
        INSERT INTO TAGGER (navn, beskrivelse)
        VALUES 
        ('natur', 'Bilder og innlegg om naturen'),
        ('mat', 'Matoppskrifter og matopplevelser'),
        ('teknologi', 'Alt om teknologi og digitale trender'),
        ('reise', 'Reiseopplevelser og reisetips')
        ''')
        
        # Add sample posts
        db.execute('''
        INSERT INTO INNLEGG (innhold, opprettet_dato, synlighet, bruker_id)
        VALUES 
        ('Fantastisk solnedgang fra fjellturen i dag! #natur #fjelltur', '2023-07-01 18:45:00', 'offentlig', 1),
        ('Ny oppskrift på hjemmelaget pasta med sesongbaserte råvarer. Deilig sommermat!', '2023-07-02 12:30:00', 'offentlig', 2),
        ('Har nettopp lært meg grunnleggende Python-programmering. Fascinerende!', '2023-07-03 09:15:00', 'offentlig', 3)
        ''')
        
        # Connect posts with tags
        db.execute('''
        INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id)
        VALUES 
        (1, 1), -- nature tag for post 1
        (2, 2), -- food tag for post 2
        (3, 3)  -- technology tag for post 3
        ''')
        
        # Add sample comments
        db.execute('''
        INSERT INTO KOMMENTARER (innhold, opprettet_dato, innlegg_id, bruker_id, forelder_kommentar_id)
        VALUES 
        ('Nydelig bilde! Hvor er dette tatt?', '2023-07-01 19:10:00', 1, 2, NULL),
        ('Det var i Hardanger. Takk!', '2023-07-01 20:00:00', 1, 1, 1),
        ('Ser fantastisk ut! Må prøve denne oppskriften.', '2023-07-02 13:05:00', 2, 3, NULL)
        ''')
        
        # Add sample reactions
        db.execute('''
        INSERT INTO REAKSJONER (reaksjon_type, opprettet_dato, bruker_id, innlegg_id, kommentar_id)
        VALUES 
        ('like', '2023-07-01 19:05:00', 2, 1, NULL),
        ('love', '2023-07-01 19:30:00', 3, 1, NULL),
        ('like', '2023-07-02 13:10:00', 1, 2, NULL)
        ''')
        
        print("Sample data added successfully")