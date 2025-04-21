import os
from flask import Flask

def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'social_media.db'),
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register the database commands
    from . import database
    database.init_app(app)

    # Register blueprints (routes)
    from .routes import users, posts, comments
    app.register_blueprint(users.bp)
    app.register_blueprint(posts.bp)
    app.register_blueprint(comments.bp)
    
    # Make url_for('index') work by setting up a default route
    app.add_url_rule('/', endpoint='index', view_func=posts.index)

    return app