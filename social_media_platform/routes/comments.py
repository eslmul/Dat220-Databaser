from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from social_media_platform.database import get_db

bp = Blueprint('comments', __name__, url_prefix='/comments')

@bp.route('/create/<int:post_id>', methods=('POST',))
def create(post_id):
    """Create a new comment on a post."""
    innhold = request.form['innhold']
    parent_id = request.form.get('parent_id', None)
    error = None

    if not innhold:
        error = 'Kommentarinnhold er påkrevd.'

    if error is None:
        db = get_db()
        # Hardcoded user_id for now (in a real app, this would come from the logged in user)
        user_id = 1
        
        db.execute(
            'INSERT INTO KOMMENTARER (innhold, innlegg_id, bruker_id, forelder_kommentar_id)'
            ' VALUES (?, ?, ?, ?)',
            (innhold, post_id, user_id, parent_id)
        )
        db.commit()
        
        flash('Kommentar lagt til.')
    else:
        flash(error)
        
    return redirect(url_for('posts.show', id=post_id))

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
def update(id):
    """Update a comment."""
    comment = get_comment(id)
    
    if request.method == 'POST':
        innhold = request.form['innhold']
        error = None

        if not innhold:
            error = 'Kommentarinnhold er påkrevd.'

        if error is None:
            db = get_db()
            db.execute(
                'UPDATE KOMMENTARER SET innhold = ?'
                ' WHERE kommentar_id = ?',
                (innhold, id)
            )
            db.commit()
            
            # Get the post_id to redirect back to the post
            post_id = comment['innlegg_id']
            flash('Kommentar oppdatert.')
            return redirect(url_for('posts.show', id=post_id))

        flash(error)
    
    return render_template('comments/update.html', comment=comment)

@bp.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    """Delete a comment."""
    comment = get_comment(id)
    post_id = comment['innlegg_id']
    
    db = get_db()
    db.execute('DELETE FROM KOMMENTARER WHERE kommentar_id = ?', (id,))
    db.commit()
    
    flash('Kommentar slettet.')
    return redirect(url_for('posts.show', id=post_id))

def get_comment(id, check_author=True):
    """Get a comment by id."""
    comment = get_db().execute(
        'SELECT k.*, b.brukernavn'
        ' FROM KOMMENTARER k JOIN BRUKERE b ON k.bruker_id = b.bruker_id'
        ' WHERE k.kommentar_id = ?',
        (id,)
    ).fetchone()

    if comment is None:
        abort(404, f"Kommentar id {id} finnes ikke.")

    # In a real application, we would check if the current user is the author
    # For now, we'll skip this check for simplicity
    # if check_author and comment['bruker_id'] != g.user['id']:
    #     abort(403)

    return comment

@bp.route('/by-user/<int:user_id>')
def by_user(user_id):
    """Show comments by a specific user."""
    db = get_db()
    
    # Get user info
    user = db.execute(
        'SELECT * FROM BRUKERE WHERE bruker_id = ?',
        (user_id,)
    ).fetchone()
    
    if user is None:
        abort(404, f"Bruker id {user_id} finnes ikke.")
    
    # Get all comments by the user
    comments = db.execute(
        'SELECT k.*, i.innhold as post_content, b.brukernavn'
        ' FROM KOMMENTARER k'
        ' JOIN INNLEGG i ON k.innlegg_id = i.innlegg_id'
        ' JOIN BRUKERE b ON k.bruker_id = b.bruker_id'
        ' WHERE k.bruker_id = ?'
        ' ORDER BY k.opprettet_dato DESC',
        (user_id,)
    ).fetchall()
    
    return render_template('comments/by_user.html', comments=comments, user=user)