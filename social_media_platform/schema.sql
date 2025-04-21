-- SQLite schema for social media platform

-- Drop tables if they exist
DROP TABLE IF EXISTS INNLEGG_TAGGER;
DROP TABLE IF EXISTS MELDINGER;
DROP TABLE IF EXISTS FØLGER;
DROP TABLE IF EXISTS REAKSJONER;
DROP TABLE IF EXISTS KOMMENTARER;
DROP TABLE IF EXISTS INNLEGG;
DROP TABLE IF EXISTS TAGGER;
DROP TABLE IF EXISTS BRUKERE;

-- Create BRUKERE (Users) table
CREATE TABLE BRUKERE (
    bruker_id INTEGER PRIMARY KEY AUTOINCREMENT,
    brukernavn TEXT NOT NULL UNIQUE,
    epost TEXT NOT NULL UNIQUE,
    passord_hash TEXT NOT NULL,
    profilbilde TEXT,
    bio TEXT,
    registrerings_dato TEXT NOT NULL DEFAULT (date('now')),
    fødselsdato TEXT,
    status TEXT DEFAULT 'aktiv'
);

-- Create INNLEGG (Posts) table
CREATE TABLE INNLEGG (
    innlegg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    innhold TEXT NOT NULL,
    opprettet_dato TEXT NOT NULL DEFAULT (datetime('now')),
    oppdatert_dato TEXT DEFAULT (datetime('now')),
    synlighet TEXT NOT NULL DEFAULT 'offentlig',
    bruker_id INTEGER NOT NULL,
    FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE
);

-- Create KOMMENTARER (Comments) table
CREATE TABLE KOMMENTARER (
    kommentar_id INTEGER PRIMARY KEY AUTOINCREMENT,
    innhold TEXT NOT NULL,
    opprettet_dato TEXT NOT NULL DEFAULT (datetime('now')),
    innlegg_id INTEGER NOT NULL,
    bruker_id INTEGER NOT NULL,
    forelder_kommentar_id INTEGER,
    FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
    FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (forelder_kommentar_id) REFERENCES KOMMENTARER(kommentar_id) ON DELETE SET NULL
);

-- Create REAKSJONER (Reactions) table
CREATE TABLE REAKSJONER (
    reaksjon_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reaksjon_type TEXT NOT NULL,  -- like, love, laugh, etc.
    opprettet_dato TEXT NOT NULL DEFAULT (datetime('now')),
    bruker_id INTEGER NOT NULL,
    innlegg_id INTEGER,
    kommentar_id INTEGER,
    FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
    FOREIGN KEY (kommentar_id) REFERENCES KOMMENTARER(kommentar_id) ON DELETE CASCADE,
    -- SQLite doesn't support CHECK constraints directly like MySQL
    -- We'll handle this validation in our application code
    CHECK ((innlegg_id IS NOT NULL AND kommentar_id IS NULL) OR
           (innlegg_id IS NULL AND kommentar_id IS NOT NULL))
);

-- Create FØLGER (Follows) table
CREATE TABLE FØLGER (
    følge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    følger_id INTEGER NOT NULL,  -- User who is following
    følger_bruker_id INTEGER NOT NULL,  -- User being followed
    opprettet_dato TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT DEFAULT 'aktiv',
    FOREIGN KEY (følger_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (følger_bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    -- SQLite doesn't support CHECK constraints directly like MySQL
    -- We'll handle this validation in our application code
    CHECK (følger_id != følger_bruker_id),
    UNIQUE(følger_id, følger_bruker_id)
);

-- Create MELDINGER (Messages) table
CREATE TABLE MELDINGER (
    melding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    innhold TEXT NOT NULL,
    sendt_dato TEXT NOT NULL DEFAULT (datetime('now')),
    lest_dato TEXT,
    avsender_id INTEGER NOT NULL,
    mottaker_id INTEGER NOT NULL,
    FOREIGN KEY (avsender_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (mottaker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE
);

-- Create TAGGER (Tags) table
CREATE TABLE TAGGER (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    navn TEXT NOT NULL UNIQUE,
    beskrivelse TEXT
);

-- Create INNLEGG_TAGGER (Post-Tags) junction table for many-to-many relationship
CREATE TABLE INNLEGG_TAGGER (
    innlegg_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (innlegg_id, tag_id),
    FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES TAGGER(tag_id) ON DELETE CASCADE
);

-- Create indexes for common queries
CREATE INDEX idx_innlegg_opprettet_bruker ON INNLEGG(opprettet_dato, bruker_id);
CREATE INDEX idx_kommentarer_innlegg_bruker ON KOMMENTARER(innlegg_id, bruker_id);
CREATE INDEX idx_brukernavn ON BRUKERE(brukernavn);
CREATE INDEX idx_epost ON BRUKERE(epost);
CREATE INDEX idx_reaksjoner_innlegg ON REAKSJONER(innlegg_id);
CREATE INDEX idx_reaksjoner_kommentar ON REAKSJONER(kommentar_id);
CREATE INDEX idx_følger_id ON FØLGER(følger_id);
CREATE INDEX idx_følger_bruker_id ON FØLGER(følger_bruker_id);
CREATE INDEX idx_meldinger_avsender ON MELDINGER(avsender_id);
CREATE INDEX idx_meldinger_mottaker ON MELDINGER(mottaker_id);