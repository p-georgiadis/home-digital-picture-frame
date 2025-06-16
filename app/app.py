# app.py
import os
import subprocess
from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory
from app.models import Session, MediaItem
from PIL import Image
import logging
import msal, uuid

# Load environment variables for Azure AD authentication
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
ALLOWED_EMAIL = os.getenv("ALLOWED_EMAIL", "").lower()

if not CLIENT_ID or not CLIENT_SECRET or not FLASK_SECRET_KEY:
    raise RuntimeError("Missing required environment variables: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, FLASK_SECRET_KEY")

TENANT_ID = os.getenv("AZURE_TENANT_ID", "consumers")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_PATH = "/auth/callback"
SCOPE = ["User.Read"]
SESSION_KEY = "user"

# Configure logging
waitress_logger = logging.getLogger('waitress')
waitress_logger.setLevel(logging.WARNING)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, '..', 'static')
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
THUMB_DIR = os.path.join(MEDIA_DIR, 'thumbnails')

# Ensure media directories exist
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = FLASK_SECRET_KEY

os.makedirs(THUMB_DIR, exist_ok=True)

def _build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache)

def _build_auth_url():
    return _build_msal_app().get_authorization_request_url(
        scopes=SCOPE,
        state=str(uuid.uuid4()),
        redirect_uri=url_for("authorized", _external=True))

@app.route("/login")
def login():
    return redirect(_build_auth_url())

@app.route(REDIRECT_PATH)
def authorized():
    if request.args.get("error"):
        return f"Error: {request.args['error']} – {request.args.get('error_description')}", 400
    if "code" not in request.args:
        return "No code returned", 400

    result = _build_msal_app().acquire_token_by_authorization_code(
        request.args["code"],
        scopes=SCOPE,
        redirect_uri=url_for("authorized", _external=True))

    if "id_token_claims" in result:
        claims = result["id_token_claims"]

        # Grab email from whichever claim is present
        user_email = (claims.get("email")
                      or claims.get("preferred_username", "")).lower()

        if user_email != ALLOWED_EMAIL:
            return "Access denied", 403

        session[SESSION_KEY] = claims
        return redirect(url_for("admin"))
    return "Could not acquire token", 500

@app.route("/logout")
def logout():
    session.pop(SESSION_KEY, None)
    signout_url = f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri=" \
                  + url_for('admin', _external=True)
    return redirect(signout_url)

def get_video_duration(filepath):
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        filepath
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        duration_str = result.stdout.strip()
        return float(duration_str)
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess failed: {e}")
        return None

def create_image_thumbnail(image_path, thumb_path, size=(150, 150)):
    with Image.open(image_path) as img:
        img.thumbnail(size)
        img.save(thumb_path)

def create_video_thumbnail(video_path, thumb_path):
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-ss', '00:00:01.000',
        '-vframes', '1',
        '-q:v', '2',
        thumb_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess failed: {e}")

@app.route('/admin')
def admin():
    is_auth = session.get(SESSION_KEY) is not None
    media_items = []
    if is_auth:
        with Session() as db_session:
            media_items = db_session.query(MediaItem).all()
    return render_template('admin.html',
                           media_items=media_items,
                           authenticated=is_auth)

@app.route('/admin/upload', methods=['POST'])
def upload():
    if session.get(SESSION_KEY) is None:
        return redirect(url_for('admin'))

    file = request.files.get('file')
    if file and file.filename:
        filename = file.filename
        extension = os.path.splitext(filename)[1].lower()
        filepath = os.path.join(MEDIA_DIR, filename)

        if os.path.exists(filepath):
            return "File already exists", 400

        file.save(filepath)

        if extension in ['.jpg', '.jpeg', '.png']:
            ftype = 'image'
            duration = None
            thumb_path = os.path.join(THUMB_DIR, filename)
            create_image_thumbnail(filepath, thumb_path)
        elif extension in ['.mp4', '.mov']:
            ftype = 'video'
            duration = get_video_duration(filepath)
            thumb_filename = os.path.splitext(filename)[0] + ".jpg"
            thumb_path = os.path.join(THUMB_DIR, thumb_filename)
            create_video_thumbnail(filepath, thumb_path)
        else:
            return "Unsupported file type", 400

        with Session() as db_session:
            item = MediaItem(filename=filename, filetype=ftype, duration=duration)
            db_session.add(item)
            db_session.commit()

    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:item_id>')
def delete_item(item_id):
    if session.get(SESSION_KEY) is None:
        return redirect(url_for('admin'))
    with Session() as db_session:
        item = db_session.query(MediaItem).filter_by(id=item_id).first()
        if item:
            filepath = os.path.join(MEDIA_DIR, item.filename)
            if item.filetype == 'image':
                thumb_path = os.path.join(THUMB_DIR, item.filename)
            else:
                base_name = os.path.splitext(item.filename)[0]
                thumb_path = os.path.join(THUMB_DIR, base_name + '.jpg')

            if os.path.exists(filepath):
                os.remove(filepath)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)

            db_session.delete(item)
            db_session.commit()
    return redirect(url_for('admin'))

@app.route('/display')
def display():
    if 'current_index' not in session:
        session['current_index'] = 0

    with Session() as db_session:
        media_items = db_session.query(MediaItem).all()

    if not media_items:
        return render_template('single_media.html', media_url=None, is_video=False, refresh_interval=10)

    current_index = session['current_index'] % len(media_items)
    media = media_items[current_index]
    session['current_index'] += 1

    is_video = (media.filetype == 'video')
    media_url = f"/media/{media.filename}"

    if is_video and media.duration:
        refresh_interval = int(media.duration) + 1
    else:
        refresh_interval = 10

    return render_template('single_media.html', media_url=media_url, is_video=is_video, refresh_interval=refresh_interval)

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_DIR, filename)

@app.teardown_appcontext
def shutdown_session(exception=None):
    Session.remove()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
