"""
Script for å importere testdata fra social_media_sample_data.sql til databasen.
"""

def import_sql_sample_data():
    """
    Import sample data from the social_media_sample_data.sql file.
    This function reads the SQL file and executes the insert statements.
    
    Returns:
        bool: True if import was successful, False otherwise
    """
    try:
        from db_config import Database
        import os
        
        # Sjekk om filen eksisterer
        sql_file_path = 'MySQL/social_media_sample_data.sql'
        if not os.path.exists(sql_file_path):
            print(f"Finner ikke SQL-fil: {sql_file_path}")
            # Prøv alternativ plassering
            alternative_paths = [
                'social_media_sample_data.sql',
                './social_media_sample_data.sql',
                '../social_media_sample_data.sql'
            ]
            
            for alt_path in alternative_paths:
                if os.path.exists(alt_path):
                    sql_file_path = alt_path
                    print(f"Fant SQL-fil på alternativ plassering: {alt_path}")
                    break
            else:
                print("Kunne ikke finne SQL-filen.")
                return False
        
        print(f"Leser inn testdata fra: {sql_file_path}")
        
        # Les inn SQL-filen
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Del opp scriptet i individuelle spørringer
        import re
        
        # Fjern kommentarer og tom plass
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
        
        # Filtrer ut bare INSERT-statements
        insert_statements = [stmt for stmt in statements if stmt.upper().startswith('INSERT')]
        
        # Utfør INSERT-spørringene
        with Database() as db:
            # Sjekk først om det allerede finnes data
            user_count = db.fetchone("SELECT COUNT(*) as count FROM BRUKERE")
            if user_count and user_count['count'] > 0:
                print(f"Det finnes allerede {user_count['count']} brukere i databasen.")
                proceed = input("Ønsker du å tømme databasen og importere testdata? (y/n): ")
                if proceed.lower() != 'y':
                    print("Import avbrutt.")
                    return False
                
                # Tøm databasen
                print("Tømmer databasen...")
                db.execute("DELETE FROM INNLEGG_TAGGER")
                db.execute("DELETE FROM MELDINGER")
                db.execute("DELETE FROM FØLGER")
                db.execute("DELETE FROM REAKSJONER") 
                db.execute("DELETE FROM KOMMENTARER")
                db.execute("DELETE FROM INNLEGG")
                db.execute("DELETE FROM TAGGER")
                db.execute("DELETE FROM BRUKERE")
            
            print(f"Legger inn {len(insert_statements)} INSERT-spørringer...")
            
            # Kjør hver INSERT-spørring
            for i, statement in enumerate(insert_statements):
                try:
                    # Erstatt MySQL-spesifikk syntaks med SQLite-kompatibel syntaks
                    # For eksempel, erstatt 'NOW()' med 'CURRENT_TIMESTAMP'
                    statement = statement.replace('NOW()', 'CURRENT_TIMESTAMP')
                    
                    db.execute(statement)
                    if (i+1) % 5 == 0:
                        print(f"  Progress: {i+1}/{len(insert_statements)} statements")
                except Exception as e:
                    print(f"Feil ved utføring av spørring {i+1}: {e}")
                    print(f"Spørring: {statement}")
                    # Fortsett med neste spørring
            
            print("Import av testdata fullført!")
            return True
            
    except Exception as e:
        print(f"Feil ved import av testdata: {e}")
        return False

if __name__ == "__main__":
    # Kjør importfunksjonen direkte når scriptet kjøres
    import_sql_sample_data()