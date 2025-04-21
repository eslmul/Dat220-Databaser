#!/bin/bash
source venv/bin/activate
export FLASK_APP=social_media_platform
export FLASK_ENV=development
flask run

# make it executable by running:
# chmod +x run.sh
# This script sets up the virtual environment and runs the Flask application.
# To run the application, use the following command:
# ./run.sh