from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from werkzeug.security import check_password_hash, generate_password_hash

from social_media_platform.database import get_db

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/')
def index():
    """Show all users."""
    db = get_db()
    users = db.execute(
        'SELECT bruker_id, brukernavn, epost, profilbilde, bio, status FROM BRUKERE'
    ).fetchall()
    return render_template('users/index.html', users=users)

@bp.route('/<int:id>')
def show(id):
    """Show a single user and their posts."""
    user = get_user(id)
    
    db = get_db()
    # Get user's posts
    posts = db.execute(
        'SELECT i.*, b.brukernavn'
        ' FROM INNLEGG i JOIN BRUKERE b ON i.bruker_id = b.bruker_id'
        ' WHERE i.bruker_id = ?'
        ' ORDER BY i.opprettet_dato DESC',
        (id,)
    ).fetchall()
    
    # Get follower count
    follower_count = db.execute(
        'SELECT COUNT(*) as count FROM FØLGER WHERE følger_bruker_id = ? AND status = "aktiv"',
        (id,)
    ).fetchone()['count']
    
    # Get following count
    following_count = db.execute(
        'SELECT COUNT(*) as count FROM FØLGER WHERE følger_id = ? AND status = "aktiv"',
        (id,)
    ).fetchone()['count']
    
    return render_template('users/show.html', user=user, posts=posts, 
                          follower_count=follower_count, following_count=following_count)

@bp.route('/create', methods=('GET', 'POST'))
def create():
    """Create a new user."""
    if request.method == 'POST':
        brukernavn = request.form['brukernavn']
        epost = request.form['epost']
        passord = request.form['passord']
        profilbilde = request.form['profilbilde']
        bio = request.form['bio']
        fødselsdato = request.form['fødselsdato']
        error = None

        if not brukernavn:
            error = 'Brukernavn er påkrevd.'
        elif not epost:
            error = 'E-post er påkrevd.'
        elif not passord:
            error = 'Passord er påkrevd.'

        if error is None:
            db = get_db()
            try:
                db.execute(
                    'INSERT INTO BRUKERE (brukernavn, epost, passord_hash, profilbilde, bio, fødselsdato)'
                    ' VALUES (?, ?, ?, ?, ?, ?)',
                    (brukernavn, epost, generate_password_hash(passord), profilbilde, bio, fødselsdato)
                )
                db.commit()
            except db.IntegrityError:
                error = f"Bruker {brukernavn} eller e-post {epost} eksisterer allerede."
            else:
                return redirect(url_for('users.index'))

        flash(error)

    return render_template('users/create.html')

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
def update(id):
    """Update a user's information."""
    user = get_user(id)

    if request.method == 'POST':
        brukernavn = request.form['brukernavn']
        epost = request.form['epost']
        profilbilde = request.form['profilbilde']
        bio = request.form['bio']
        error = None

        if not brukernavn:
            error = 'Brukernavn er påkrevd.'
        elif not epost:
            error = 'E-post er påkrevd.'

        if error is None:
            db = get_db()
            try:
                db.execute(
                    'UPDATE BRUKERE SET brukernavn = ?, epost = ?, profilbilde = ?, bio = ?'
                    ' WHERE bruker_id = ?',
                    (brukernavn, epost, profilbilde, bio, id)
                )
                db.commit()
            except db.IntegrityError:
                error = f"Bruker {brukernavn} eller e-post {epost} eksisterer allerede."
            else:
                return redirect(url_for('users.show', id=id))

        flash(error)

    return render_template('users/update.html', user=user)

@bp.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    """Delete a user."""
    get_user(id)
    db = get_db()
    db.execute('DELETE FROM BRUKERE WHERE bruker_id = ?', (id,))
    db.commit()
    flash(f'Bruker med ID {id} er slettet.')
    return redirect(url_for('users.index'))

def get_user(id):
    """Get a user by id."""
    user = get_db().execute(
        'SELECT * FROM BRUKERE WHERE bruker_id = ?',
        (id,)
    ).fetchone()

    if user is None:
        abort(404, f"Bruker med id {id} finnes ikke.")

    return user