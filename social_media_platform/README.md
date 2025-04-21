# Social Media Platform Database

A simple social media platform with a Flask web application and SQLite database.

## Features

- User management (CRUD operations)
- Post management (CRUD operations)
- Comments and nested replies
- Reactions/likes
- Tag system for posts
- Search functionality
- Follows and messaging system (database structure only)

## Database Design

The database follows a normalized structure (3NF) with the following main entities:

- BRUKERE (Users)
- INNLEGG (Posts)
- KOMMENTARER (Comments)
- REAKSJONER (Reactions)
- FØLGER (Follows)
- MELDINGER (Messages)
- TAGGER (Tags)
- INNLEGG_TAGGER (Post-Tag many-to-many relationship)

## Installation

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. Install the dependencies:
   ```
   pip install Flask
   ```

4. Set up the Flask application:
   ```
   export FLASK_APP=social_media_platform
   export FLASK_ENV=development
   ```
   
   On Windows:
   ```
   set FLASK_APP=social_media_platform
   set FLASK_ENV=development
   ```

5. Initialize the database:
   ```
   flask init-db
   ```

6. Seed the database with sample data:
   ```
   flask seed-db
   ```

7. Run the application:
   ```
   flask run
   ```

8. Visit `http://127.0.0.1:5000/` in your browser to access the application.

## Project Structure

```
social_media_platform/
├── app.py               # Main Flask application
├── schema.sql           # SQLite database schema
├── database.py          # Database connection and helper functions
├── routes/              # Route handlers
├── templates/           # HTML templates
├── static/              # Static assets (CSS, JS)
└── instance/            # SQLite database file location
```

## SQL Queries

This application implements various types of SQL queries:

1. **Joins**:
   - Posts with user information
   - Comments with user information
   - Posts with tags

2. **Aggregation**:
   - Count of comments per post
   - Count of reactions per post
   - Count of followers/following

3. **Search/Filter**:
   - Search posts by content
   - Filter posts by tag
   - Filter comments by user

4. **Grouping**:
   - Group reactions by type
   - Group posts by tag

## License

This project is created for educational purposes.