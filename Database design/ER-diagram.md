# ER-diagram for sosial media-plattform

```mermaid
erDiagram
    BRUKERE {
        int bruker_id PK
        string brukernavn
        string epost
        string passord_hash
        string profilbilde
        text bio
        date registrerings_dato
        date fødselsdato
        string status
    }
    
    INNLEGG {
        int innlegg_id PK
        text innhold
        datetime opprettet_dato
        datetime oppdatert_dato
        string synlighet
        int bruker_id FK
    }
    
    KOMMENTARER {
        int kommentar_id PK
        text innhold
        datetime opprettet_dato
        int innlegg_id FK
        int bruker_id FK
        int forelder_kommentar_id FK
    }
    
    REAKSJONER {
        int reaksjon_id PK
        string reaksjon_type
        datetime opprettet_dato
        int bruker_id FK
        int innlegg_id FK
        int kommentar_id FK
    }
    
    FØLGER {
        int følge_id PK
        int følger_id FK
        int følger_bruker_id FK
        datetime opprettet_dato
        string status
    }
    
    MELDINGER {
        int melding_id PK
        text innhold
        datetime sendt_dato
        datetime lest_dato
        int avsender_id FK
        int mottaker_id FK
    }
    
    TAGGER {
        int tag_id PK
        string navn
        text beskrivelse
    }
    
    INNLEGG_TAGGER {
        int innlegg_id FK
        int tag_id FK
    }
    
    BRUKERE ||--o{ INNLEGG : "oppretter"
    BRUKERE ||--o{ KOMMENTARER : "skriver"
    INNLEGG ||--o{ KOMMENTARER : "har"
    BRUKERE ||--o{ REAKSJONER : "gir"
    INNLEGG ||--o{ REAKSJONER : "mottar"
    KOMMENTARER ||--o{ REAKSJONER : "mottar"
    BRUKERE ||--o{ FØLGER : "følger som følger"
    BRUKERE ||--o{ FØLGER : "følges av som følges"
    BRUKERE ||--o{ MELDINGER : "sender"
    BRUKERE ||--o{ MELDINGER : "mottar"
    INNLEGG ||--o{ INNLEGG_TAGGER : "har"
    TAGGER ||--o{ INNLEGG_TAGGER : "tilknyttet til"
    