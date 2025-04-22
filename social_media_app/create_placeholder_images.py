"""
Dette scriptet oppretter placeholder-bilder som kan brukes for brukere
hvis vi ikke har faktiske bilder tilgjengelig i databasen.
"""

import os
from PIL import Image, ImageDraw, ImageFont
import random

def create_placeholder_images():
    print("Oppretter placeholder-bilder...")
    
    # Sørg for at uploads-mappen eksisterer
    upload_dir = 'static/uploads'
    os.makedirs(upload_dir, exist_ok=True)
    
    # Fargepalett for bildene
    colors = [
        (52, 152, 219),    # blå
        (231, 76, 60),     # rød
        (46, 204, 113),    # grønn
        (155, 89, 182),    # lilla
        (241, 196, 15),    # gul
        (230, 126, 34),    # oransje
        (26, 188, 156),    # turkis
        (243, 156, 18)     # amber
    ]
    
    # Generer profilbilder for brukere
    for i in range(1, 13):  # profil1.jpg til profil12.jpg
        filename = f'profil{i}.jpg'
        filepath = os.path.join(upload_dir, filename)
        
        # Sjekk om filen allerede eksisterer
        if os.path.exists(filepath):
            print(f"  {filename} finnes allerede, hopper over...")
            continue
        
        # Opprett et 300x300 bilde
        img = Image.new('RGB', (300, 300), color=random.choice(colors))
        draw = ImageDraw.Draw(img)
        
        # Prøv å laste inn en font (hvis ikke tilgjengelig, bruker standard)
        try:
            # Dette kan feile på noen systemer
            font = ImageFont.truetype("arial.ttf", 120)
        except IOError:
            try:
                # Prøv en annen systemfont
                font = ImageFont.truetype("DejaVuSans.ttf", 120)
            except IOError:
                # Hvis ingen font er tilgjengelig, bruk standard
                font = ImageFont.load_default()
        
        # Legg til en bokstav i midten (første bokstav i filnavnet)
        initial = chr(64 + i)  # A, B, C, ...
        text_width, text_height = draw.textsize(initial, font=font) if hasattr(draw, 'textsize') else (120, 120)
        position = ((300 - text_width) // 2, (300 - text_height) // 2)
        draw.text(position, initial, font=font, fill="white")
        
        # Lagre bildet
        img.save(filepath, 'JPEG', quality=95)
        print(f"  Opprettet {filename}")
    
    # Opprett et standardbilde
    default_path = os.path.join(upload_dir, 'default.jpg')
    if not os.path.exists(default_path):
        img = Image.new('RGB', (300, 300), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except IOError:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 80)
            except IOError:
                font = ImageFont.load_default()
        
        text = "Profil"
        text_width, text_height = draw.textsize(text, font=font) if hasattr(draw, 'textsize') else (120, 80)
        position = ((300 - text_width) // 2, (300 - text_height) // 2)
        draw.text(position, text, font=font, fill="white")
        
        img.save(default_path, 'JPEG', quality=95)
        print("  Opprettet default.jpg")
    
    print("Placeholder-bilder opprettet!")

if __name__ == "__main__":
    try:
        create_placeholder_images()
    except Exception as e:
        print(f"Feil ved oppretting av placeholder-bilder: {e}")
        print("Forsøk å installere PIL/Pillow biblioteket med: pip install Pillow")