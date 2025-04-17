-- social_media_schema.sql
-- Database schema for social media platform

-- Drop tables if they exist (in reverse order of creation to handle foreign key constraints)
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
    bruker_id INT AUTO_INCREMENT PRIMARY KEY,
    brukernavn VARCHAR(50) NOT NULL UNIQUE,
    epost VARCHAR(100) NOT NULL UNIQUE,
    passord_hash VARCHAR(255) NOT NULL,
    profilbilde VARCHAR(255),
    bio TEXT,
    registrerings_dato DATE NOT NULL DEFAULT (CURRENT_DATE),
    fødselsdato DATE,
    status VARCHAR(20) DEFAULT 'aktiv',
    
    -- Adding indexes for frequently queried fields
    INDEX idx_brukernavn (brukernavn),
    INDEX idx_epost (epost),
    INDEX idx_status (status)
);

-- Create INNLEGG (Posts) table
CREATE TABLE INNLEGG (
    innlegg_id INT AUTO_INCREMENT PRIMARY KEY,
    innhold TEXT NOT NULL,
    opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    oppdatert_dato DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    synlighet VARCHAR(20) NOT NULL DEFAULT 'offentlig',
    bruker_id INT NOT NULL,
    
    -- Foreign key constraint to BRUKERE
    FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    
    -- Adding indexes for frequently queried fields
    INDEX idx_bruker_id (bruker_id),
    INDEX idx_opprettet_dato (opprettet_dato),
    INDEX idx_synlighet (synlighet)
);

-- Create KOMMENTARER (Comments) table
CREATE TABLE KOMMENTARER (
    kommentar_id INT AUTO_INCREMENT PRIMARY KEY,
    innhold TEXT NOT NULL,
    opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    innlegg_id INT NOT NULL,
    bruker_id INT NOT NULL,
    forelder_kommentar_id INT,
    
    -- Foreign key constraints
    FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
    FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (forelder_kommentar_id) REFERENCES KOMMENTARER(kommentar_id) ON DELETE SET NULL,
    
    -- Adding indexes for frequently queried fields
    INDEX idx_innlegg_id (innlegg_id),
    INDEX idx_bruker_id (bruker_id),
    INDEX idx_forelder_kommentar_id (forelder_kommentar_id)
);

-- Create REAKSJONER (Reactions) table
CREATE TABLE REAKSJONER (
    reaksjon_id INT AUTO_INCREMENT PRIMARY KEY,
    reaksjon_type VARCHAR(20) NOT NULL,  -- like, love, laugh, etc.
    opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    bruker_id INT NOT NULL,
    innlegg_id INT,
    kommentar_id INT,
    
    -- Foreign key constraints
    FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
    FOREIGN KEY (kommentar_id) REFERENCES KOMMENTARER(kommentar_id) ON DELETE CASCADE,
    
    -- Check constraint to ensure either innlegg_id or kommentar_id is set, but not both
    CONSTRAINT check_reaction_target CHECK (
        (innlegg_id IS NOT NULL AND kommentar_id IS NULL) OR
        (innlegg_id IS NULL AND kommentar_id IS NOT NULL)
    ),
    
    -- Adding indexes for frequently queried fields
    INDEX idx_bruker_id (bruker_id),
    INDEX idx_innlegg_id (innlegg_id),
    INDEX idx_kommentar_id (kommentar_id),
    INDEX idx_reaksjon_type (reaksjon_type)
);

-- Create FØLGER (Follows) table
CREATE TABLE FØLGER (
    følge_id INT AUTO_INCREMENT PRIMARY KEY,
    følger_id INT NOT NULL,  -- User who is following
    følger_bruker_id INT NOT NULL,  -- User being followed
    opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'aktiv',
    
    -- Foreign key constraints
    FOREIGN KEY (følger_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (følger_bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    
    -- Constraint to prevent self-following
    CONSTRAINT prevent_self_follow CHECK (følger_id != følger_bruker_id),
    
    -- Unique constraint to prevent duplicate follows
    UNIQUE KEY unique_follow (følger_id, følger_bruker_id),
    
    -- Adding indexes for frequently queried fields
    INDEX idx_følger_id (følger_id),
    INDEX idx_følger_bruker_id (følger_bruker_id),
    INDEX idx_status (status)
);

-- Create MELDINGER (Messages) table
CREATE TABLE MELDINGER (
    melding_id INT AUTO_INCREMENT PRIMARY KEY,
    innhold TEXT NOT NULL,
    sendt_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lest_dato DATETIME,
    avsender_id INT NOT NULL,
    mottaker_id INT NOT NULL,
    
    -- Foreign key constraints
    FOREIGN KEY (avsender_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (mottaker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    
    -- Adding indexes for frequently queried fields
    INDEX idx_avsender_id (avsender_id),
    INDEX idx_mottaker_id (mottaker_id),
    INDEX idx_sendt_dato (sendt_dato),
    INDEX idx_lest_dato (lest_dato)
);

-- Create TAGGER (Tags) table
CREATE TABLE TAGGER (
    tag_id INT AUTO_INCREMENT PRIMARY KEY,
    navn VARCHAR(50) NOT NULL UNIQUE,
    beskrivelse TEXT,
    
    -- Adding index for frequently queried field
    INDEX idx_navn (navn)
);

-- Create INNLEGG_TAGGER (Post-Tags) junction table for many-to-many relationship
CREATE TABLE INNLEGG_TAGGER (
    innlegg_id INT NOT NULL,
    tag_id INT NOT NULL,
    
    -- Primary key composed of both foreign keys
    PRIMARY KEY (innlegg_id, tag_id),
    
    -- Foreign key constraints
    FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES TAGGER(tag_id) ON DELETE CASCADE
);

-- Additional indexes for common queries
CREATE INDEX idx_innlegg_opprettet_bruker ON INNLEGG(opprettet_dato, bruker_id);
CREATE INDEX idx_kommentarer_innlegg_bruker ON KOMMENTARER(innlegg_id, bruker_id);