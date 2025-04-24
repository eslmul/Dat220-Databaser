---
marp: true
theme: default
paginate: true
---

# Social Media Platform Database
## DAT220 Database Project Presentation

---

## Project Overview

- **Project Type:** Social Media Platform Database (Option A)
- **Technology Stack:** SQLite, Flask, Bootstrap, Python
- **Core Functionality:** User profiles, posts, comments, reactions, follows, tags

---

## Database Design Process

- Conducted thorough problem analysis
- Identified key entities and relationships
- Applied normalization principles (1NF → 3NF)
- Implemented relational constraints
- Created tables with appropriate keys and indexes

---

## Entity-Relationship Diagram

![width:900px](https://mermaid.ink/img/pako:eNqFVFtP3DAQ_CtWnggVBMJBOb2lFO5KQULltEcJXUdcvFkS4zi1syjlv3d8ySaZ22QPjL2zMzNnPrb3kOpCE4nJuvRVZ-OPv7YTxgwjtUTDpbAYMv9Gs9YwkHaF3bA1KfLkTjBaGLk0A3H8-oZ5GtRq0dBCCdNSj1uKJaOUQ8eSZzrrhBL1MNXWZcvwibQKVJWcBDZAuHJtbVRLrLMXQvJ8YBTQZqWlKI01qumkdvDd6Pyo5Pq7FDV1SLdaajOwRb6VxsCXz6K9E9WaWLl44EKxfwC1S8f0w_L38ePv1zWtsC6qj-3FeCvh-0JU9tGEYVlL3YPG5iFdA_A_CbXsQYfm-xWRK6ZYKrT0qXZJNnK-TscHU60NGPWojRKW5DOz_aJN5oRTavfV7p4z3u9Hb85cP5fKZYMwUbmZZxkqSUvtmVGO6lk-iwvIFKyD40KUjhwx3cLGVVBOUy7lKf92ZLNWm0CumN-7oHetMFgOCzBqhCbNHUQPZWFIjgNvn-B1S3lQ5pA6o_k2WA2D9Wr34G3YUVkdDxb16z7g_qLvGK2lCfTdjmOQ4GmjNaH2mPW4SudJ5aJ3QxcVsI_JI9mFWK5EBSe4y-KQfEh2nUCPf1zMkvZVD91rIQcI58A0BuM-mIODmVXMukVn4xr3Hg_HDm_T_1Yrjb9O0m3TRrNOhCCQlp9GzRs9R1dhrVqYNaQR4VzPGdMKk8Nl5-6BgzW4f4Rb9wCnNOJLfUDX37JWV2JOeE2bHPfPz-V0MpqcTMfAR9k0ysfj8TjPhqfD0Wj-azTJstPR12w4Hk9HZxmMsuyfIg4Bc0IvDCuosm0FBsupj9-CIbxc1nglrctlpgQnrIEBDLcFNRbCq88HKjG9OPqFaRbUYVo1tVaEF9JCv9IfZv2zzd_NofEP?type=png)

---

## Database Tables

### Core Tables
```sql
CREATE TABLE BRUKERE (
    bruker_id INTEGER PRIMARY KEY AUTOINCREMENT,
    brukernavn TEXT NOT NULL UNIQUE, epost TEXT NOT NULL UNIQUE,
    passord_hash TEXT NOT NULL, profilbilde TEXT, bio TEXT,
    registrerings_dato DATE NOT NULL DEFAULT CURRENT_DATE,
    fødselsdato DATE, status TEXT DEFAULT 'aktiv'
)

CREATE TABLE INNLEGG (
    innlegg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    innhold TEXT NOT NULL,
    opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    oppdatert_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    synlighet TEXT NOT NULL DEFAULT 'offentlig',
    bruker_id INTEGER NOT NULL,
    FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE
)
```

---

## Additional Tables

```sql
CREATE TABLE KOMMENTARER (
    kommentar_id INTEGER PRIMARY KEY AUTOINCREMENT,
    innhold TEXT NOT NULL, opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    innlegg_id INTEGER NOT NULL, bruker_id INTEGER NOT NULL, forelder_kommentar_id INTEGER,
    FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
    FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (forelder_kommentar_id) REFERENCES KOMMENTARER(kommentar_id) ON DELETE SET NULL
)

CREATE TABLE REAKSJONER (
    reaksjon_id INTEGER PRIMARY KEY AUTOINCREMENT, reaksjon_type TEXT NOT NULL,
    opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    bruker_id INTEGER NOT NULL, innlegg_id INTEGER, kommentar_id INTEGER,
    FOREIGN KEY (bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
    FOREIGN KEY (kommentar_id) REFERENCES KOMMENTARER(kommentar_id) ON DELETE CASCADE,
    CHECK ((innlegg_id IS NOT NULL AND kommentar_id IS NULL) OR
          (innlegg_id IS NULL AND kommentar_id IS NOT NULL))
)
```

---

## Additional Tables (cont.)

```sql
CREATE TABLE FØLGER (
    følge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    følger_id INTEGER NOT NULL, følger_bruker_id INTEGER NOT NULL,
    opprettet_dato DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'aktiv',
    FOREIGN KEY (følger_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    FOREIGN KEY (følger_bruker_id) REFERENCES BRUKERE(bruker_id) ON DELETE CASCADE,
    CHECK (følger_id != følger_bruker_id), UNIQUE (følger_id, følger_bruker_id)
)

CREATE TABLE TAGGER (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    navn TEXT NOT NULL UNIQUE, beskrivelse TEXT
)

CREATE TABLE INNLEGG_TAGGER (
    innlegg_id INTEGER NOT NULL, tag_id INTEGER NOT NULL,
    PRIMARY KEY (innlegg_id, tag_id),
    FOREIGN KEY (innlegg_id) REFERENCES INNLEGG(innlegg_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES TAGGER(tag_id) ON DELETE CASCADE
)
```

---

## SQL Queries: JOINs

### Posts with User Details
```sql
SELECT i.*, b.brukernavn 
FROM INNLEGG i 
JOIN BRUKERE b ON i.bruker_id = b.bruker_id 
ORDER BY i.opprettet_dato DESC
```

### Post Details with Tags and User Info
```sql
SELECT 
    i.innlegg_id, i.innhold, i.opprettet_dato, i.synlighet,
    b.bruker_id, b.brukernavn, b.profilbilde,
    GROUP_CONCAT(t.navn, ', ') as tags
FROM INNLEGG i
JOIN BRUKERE b ON i.bruker_id = b.bruker_id
LEFT JOIN INNLEGG_TAGGER it ON i.innlegg_id = it.innlegg_id
LEFT JOIN TAGGER t ON it.tag_id = t.tag_id
WHERE i.innlegg_id = ?
GROUP BY i.innlegg_id
```

---

## SQL Queries: Aggregation

### Platform Statistics
```sql
SELECT
    COUNT(DISTINCT b.bruker_id) AS total_users,
    COUNT(DISTINCT i.innlegg_id) AS total_posts,
    COUNT(DISTINCT k.kommentar_id) AS total_comments,
    COUNT(DISTINCT r.reaksjon_id) AS total_reactions,
    COUNT(DISTINCT t.tag_id) AS total_tags,
    (SELECT COUNT(*) FROM FØLGER) AS total_follows,
    ROUND(AVG(posts_per_user), 2) AS avg_posts_per_user,
    ROUND(AVG(comments_per_user), 2) AS avg_comments_per_user,
    ROUND(AVG(reactions_per_user), 2) AS avg_reactions_per_user
FROM BRUKERE b
LEFT JOIN (
    SELECT bruker_id, COUNT(*) as posts_per_user 
    FROM INNLEGG GROUP BY bruker_id
) user_posts ON b.bruker_id = user_posts.bruker_id
-- Additional joins omitted for brevity
```

---

## SQL Queries: Search/Filter

### Advanced Search with Multiple Filters
```sql
SELECT i.*, b.brukernavn, b.profilbilde,
       (SELECT COUNT(*) FROM KOMMENTARER k WHERE k.innlegg_id = i.innlegg_id) AS comment_count,
       (SELECT COUNT(*) FROM REAKSJONER r WHERE r.innlegg_id = i.innlegg_id) AS reaction_count,
       GROUP_CONCAT(t.navn, ', ') as tags
FROM INNLEGG i
JOIN BRUKERE b ON i.bruker_id = b.bruker_id
LEFT JOIN INNLEGG_TAGGER it ON i.innlegg_id = it.innlegg_id
LEFT JOIN TAGGER t ON it.tag_id = t.tag_id
WHERE 
  (? = '' OR i.opprettet_dato >= ?) AND
  (? = '' OR i.opprettet_dato <= ?) AND
  (? = '' OR i.bruker_id = ?) AND
  (? = '' OR it.tag_id = ?) AND
  (? = '' OR i.synlighet = ?) AND
  (? = '' OR i.innhold LIKE ?)
GROUP BY i.innlegg_id 
ORDER BY i.opprettet_dato DESC
```

---

## SQL Queries: GROUP BY

### Activity by Month Analysis
```sql
SELECT 
    strftime('%Y-%m', i.opprettet_dato) AS måned,
    COUNT(DISTINCT i.innlegg_id) AS antall_innlegg,
    COUNT(DISTINCT k.kommentar_id) AS antall_kommentarer,
    COUNT(DISTINCT r.reaksjon_id) AS antall_reaksjoner,
    COUNT(DISTINCT i.bruker_id) AS aktive_brukere
FROM INNLEGG i
LEFT JOIN KOMMENTARER k ON strftime('%Y-%m', i.opprettet_dato) = 
                           strftime('%Y-%m', k.opprettet_dato)
LEFT JOIN REAKSJONER r ON strftime('%Y-%m', i.opprettet_dato) = 
                          strftime('%Y-%m', r.opprettet_dato)
GROUP BY strftime('%Y-%m', i.opprettet_dato)
ORDER BY måned DESC
```

---

## Web Application Features

- **User Management:** Registration, profiles, following
- **Content Management:** Posts with tags, visibility controls
- **Social Interaction:** Comments, reactions, threaded replies
- **Analytics & Search:** Platform statistics, trends, filtering


## Summary

- Implemented a complete social media database with 7 tables
- Created a normalized, 3NF database design
- Developed comprehensive SQL queries for all requirements
- Built a web interface with full CRUD capabilities
- Implemented analytics and search functionality

---

## Thank You!
