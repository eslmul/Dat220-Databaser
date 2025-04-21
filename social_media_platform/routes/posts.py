from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from social_media_platform.database import get_db

bp = Blueprint('posts', __name__, url_prefix='/posts')

@bp.route('/')
def index():
    """Show all posts."""
    db = get_db()
    posts = db.execute(
        'SELECT i.innlegg_id, i.innhold, i.opprettet_dato, i.synlighet, i.bruker_id,'
        ' b.brukernavn'
        ' FROM INNLEGG i JOIN BRUKERE b ON i.bruker_id = b.bruker_id'
        ' WHERE i.synlighet = "offentlig"'
        ' ORDER BY i.opprettet_dato DESC'
    ).fetchall()
    
    # Convert rows to dictionaries and add tag information for each post
    post_list = []
    for post in posts:
        # Convert to dictionary
        post_dict = dict(post)
        
        # Get tag information
        tags = db.execute(
            'SELECT t.navn FROM TAGGER t'
            ' JOIN INNLEGG_TAGGER it ON t.tag_id = it.tag_id'
            ' WHERE it.innlegg_id = ?',
            (post['innlegg_id'],)
        ).fetchall()
        post_dict['tags'] = tags
        
        # Get comment count
        comment_count = db.execute(
            'SELECT COUNT(*) as count FROM KOMMENTARER WHERE innlegg_id = ?',
            (post['innlegg_id'],)
        ).fetchone()['count']
        post_dict['comment_count'] = comment_count
        
        # Get reaction count
        reaction_count = db.execute(
            'SELECT COUNT(*) as count FROM REAKSJONER WHERE innlegg_id = ?',
            (post['innlegg_id'],)
        ).fetchone()['count']
        post_dict['reaction_count'] = reaction_count
        
        post_list.append(post_dict)
    
    return render_template('posts/index.html', posts=post_list)

@bp.route('/<int:id>')
def show(id):
    """Show a single post with its comments."""
    post = get_post(id)
    
    db = get_db()
    # Get post's comments
    comments = db.execute(
        'SELECT k.*, b.brukernavn'
        ' FROM KOMMENTARER k JOIN BRUKERE b ON k.bruker_id = b.bruker_id'
        ' WHERE k.innlegg_id = ? AND k.forelder_kommentar_id IS NULL'
        ' ORDER BY k.opprettet_dato ASC',
        (id,)
    ).fetchall()
    
    # Get replies for each comment
    for comment in comments:
        replies = db.execute(
            'SELECT k.*, b.brukernavn'
            ' FROM KOMMENTARER k JOIN BRUKERE b ON k.bruker_id = b.bruker_id'
            ' WHERE k.forelder_kommentar_id = ?'
            ' ORDER BY k.opprettet_dato ASC',
            (comment['kommentar_id'],)
        ).fetchall()
        comment['replies'] = replies
    
    # Get tags for the post
    tags = db.execute(
        'SELECT t.navn FROM TAGGER t'
        ' JOIN INNLEGG_TAGGER it ON t.tag_id = it.tag_id'
        ' WHERE it.innlegg_id = ?',
        (id,)
    ).fetchall()
    
    # Get reaction information
    reactions = db.execute(
        'SELECT r.reaksjon_type, COUNT(*) as count'
        ' FROM REAKSJONER r'
        ' WHERE r.innlegg_id = ?'
        ' GROUP BY r.reaksjon_type',
        (id,)
    ).fetchall()
    
    return render_template('posts/show.html', post=post, comments=comments, 
                          tags=tags, reactions=reactions)

@bp.route('/create', methods=('GET', 'POST'))
def create():
    """Create a new post."""
    if request.method == 'POST':
        innhold = request.form['innhold']
        synlighet = request.form.get('synlighet', 'offentlig')
        tags = request.form.getlist('tags')
        error = None

        if not innhold:
            error = 'Innhold er påkrevd.'

        if error is None:
            db = get_db()
            # Hardcoded user_id for now (in a real app, this would come from the logged in user)
            user_id = 1
            
            # Insert post
            cursor = db.execute(
                'INSERT INTO INNLEGG (innhold, synlighet, bruker_id)'
                ' VALUES (?, ?, ?)',
                (innhold, synlighet, user_id)
            )
            db.commit()
            
            # Get the post ID
            post_id = cursor.lastrowid
            
            # Add tags if any were selected
            if tags:
                for tag_name in tags:
                    # Get tag ID (or create if it doesn't exist)
                    tag = db.execute(
                        'SELECT tag_id FROM TAGGER WHERE navn = ?',
                        (tag_name,)
                    ).fetchone()
                    
                    if tag is None:
                        tag_cursor = db.execute(
                            'INSERT INTO TAGGER (navn) VALUES (?)',
                            (tag_name,)
                        )
                        tag_id = tag_cursor.lastrowid
                    else:
                        tag_id = tag['tag_id']
                    
                    # Create post-tag relationship
                    db.execute(
                        'INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES (?, ?)',
                        (post_id, tag_id)
                    )
                db.commit()
            
            return redirect(url_for('posts.show', id=post_id))

        flash(error)
    
    # Get available tags for dropdown
    db = get_db()
    tags = db.execute('SELECT * FROM TAGGER').fetchall()
    
    return render_template('posts/create.html', tags=tags)

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
def update(id):
    """Update a post."""
    post = get_post(id)
    
    if request.method == 'POST':
        innhold = request.form['innhold']
        synlighet = request.form.get('synlighet', 'offentlig')
        tags = request.form.getlist('tags')
        error = None

        if not innhold:
            error = 'Innhold er påkrevd.'

        if error is None:
            db = get_db()
            # Update post
            db.execute(
                'UPDATE INNLEGG SET innhold = ?, synlighet = ?'
                ' WHERE innlegg_id = ?',
                (innhold, synlighet, id)
            )
            
            # Clear existing tags
            db.execute('DELETE FROM INNLEGG_TAGGER WHERE innlegg_id = ?', (id,))
            
            # Add new tags
            if tags:
                for tag_name in tags:
                    # Get tag ID (or create if it doesn't exist)
                    tag = db.execute(
                        'SELECT tag_id FROM TAGGER WHERE navn = ?',
                        (tag_name,)
                    ).fetchone()
                    
                    if tag is None:
                        tag_cursor = db.execute(
                            'INSERT INTO TAGGER (navn) VALUES (?)',
                            (tag_name,)
                        )
                        tag_id = tag_cursor.lastrowid
                    else:
                        tag_id = tag['tag_id']
                    
                    # Create post-tag relationship
                    db.execute(
                        'INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES (?, ?)',
                        (id, tag_id)
                    )
            
            db.commit()
            return redirect(url_for('posts.show', id=id))

        flash(error)
    
    # Get available tags for dropdown
    db = get_db()
    all_tags = db.execute('SELECT * FROM TAGGER').fetchall()
    
    # Get current tags for the post
    current_tags = db.execute(
        'SELECT t.tag_id FROM TAGGER t'
        ' JOIN INNLEGG_TAGGER it ON t.tag_id = it.tag_id'
        ' WHERE it.innlegg_id = ?',
        (id,)
    ).fetchall()
    current_tag_ids = [tag['tag_id'] for tag in current_tags]
    
    return render_template('posts/update.html', post=post, 
                          tags=all_tags, current_tag_ids=current_tag_ids)

@bp.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    """Delete a post."""
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM INNLEGG WHERE innlegg_id = ?', (id,))
    db.commit()
    flash(f'Innlegg med ID {id} er slettet.')
    return redirect(url_for('posts.index'))

def get_post(id, check_author=True):
    """Get a post and its author by id."""
    post = get_db().execute(
        'SELECT i.*, b.brukernavn'
        ' FROM INNLEGG i JOIN BRUKERE b ON i.bruker_id = b.bruker_id'
        ' WHERE i.innlegg_id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Innlegg id {id} finnes ikke.")

    # In a real application, we would check if the current user is the author
    # For now, we'll skip this check for simplicity
    # if check_author and post['bruker_id'] != g.user['id']:
    #     abort(403)

    return post

@bp.route('/by-tag/<tag_name>')
def by_tag(tag_name):
    """Show posts by tag."""
    db = get_db()
    posts = db.execute(
        'SELECT i.innlegg_id, i.innhold, i.opprettet_dato, i.synlighet, i.bruker_id,'
        ' b.brukernavn'
        ' FROM INNLEGG i'
        ' JOIN BRUKERE b ON i.bruker_id = b.bruker_id'
        ' JOIN INNLEGG_TAGGER it ON i.innlegg_id = it.innlegg_id'
        ' JOIN TAGGER t ON it.tag_id = t.tag_id'
        ' WHERE t.navn = ? AND i.synlighet = "offentlig"'
        ' ORDER BY i.opprettet_dato DESC',
        (tag_name,)
    ).fetchall()
    
    # Get tag information for each post
    for post in posts:
        tags = db.execute(
            'SELECT t.navn FROM TAGGER t'
            ' JOIN INNLEGG_TAGGER it ON t.tag_id = it.tag_id'
            ' WHERE it.innlegg_id = ?',
            (post['innlegg_id'],)
        ).fetchall()
        post['tags'] = tags
        
        # Get comment count for each post
        comment_count = db.execute(
            'SELECT COUNT(*) as count FROM KOMMENTARER WHERE innlegg_id = ?',
            (post['innlegg_id'],)
        ).fetchone()['count']
        post['comment_count'] = comment_count
    
    return render_template('posts/by_tag.html', posts=posts, tag_name=tag_name)

@bp.route('/search')
def search():
    """Search for posts by content."""
    query = request.args.get('q', '')
    
    if not query:
        return redirect(url_for('posts.index'))
    
    db = get_db()
    posts = db.execute(
        'SELECT i.innlegg_id, i.innhold, i.opprettet_dato, i.synlighet, i.bruker_id,'
        ' b.brukernavn'
        ' FROM INNLEGG i JOIN BRUKERE b ON i.bruker_id = b.bruker_id'
        ' WHERE i.innhold LIKE ? AND i.synlighet = "offentlig"'
        ' ORDER BY i.opprettet_dato DESC',
        ('%' + query + '%',)
    ).fetchall()
    
    # Get tag information for each post
    for post in posts:
        tags = db.execute(
            'SELECT t.navn FROM TAGGER t'
            ' JOIN INNLEGG_TAGGER it ON t.tag_id = it.tag_id'
            ' WHERE it.innlegg_id = ?',
            (post['innlegg_id'],)
        ).fetchall()
        post['tags'] = tags
    
    return render_template('posts/search.html', posts=posts, query=query)