# app.py
import os
import time
import subprocess
from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory
from app.models import Session, MediaItem
from PIL import Image
import logging

waitress_logger = logging.getLogger('waitress')
waitress_logger.setLevel(logging.WARNING)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, '..', 'static')
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
THUMB_DIR = os.path.join(MEDIA_DIR, 'thumbnails')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = 'CHANGE_THIS_TO_A_SECURE_KEY'

USERNAME = 'test'
PASSWORD = 'test'

current_index = 0

os.makedirs(THUMB_DIR, exist_ok=True)

def get_video_duration(filepath):
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        filepath
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        duration_str = result.stdout.strip()
        return float(duration_str)
    except:
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
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        if user == USERNAME and pw == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin.html', authenticated=False, media_items=[])
    return render_template('admin.html', authenticated=False, media_items=[])

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return render_template('admin.html', authenticated=False, media_items=[])
    db_session = Session()
    media_items = db_session.query(MediaItem).all()
    return render_template('admin.html', media_items=media_items, authenticated=True)

@app.route('/admin/upload', methods=['POST'])
def upload():
    if not session.get('logged_in'):
        return redirect(url_for('admin'))

    file = request.files.get('file')
    if file and file.filename:
        filename = file.filename
        extension = os.path.splitext(filename)[1].lower()
        filepath = os.path.join(MEDIA_DIR, filename)
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

        db_session = Session()
        item = MediaItem(filename=filename, filetype=ftype, duration=duration)
        db_session.add(item)
        db_session.commit()

    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:item_id>')
def delete_item(item_id):
    if not session.get('logged_in'):
        return redirect(url_for('admin'))
    db_session = Session()
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
    global current_index
    db_session = Session()
    media_items = db_session.query(MediaItem).all()

    if not media_items:
        return render_template('single_media.html', media_url=None, is_video=False, refresh_interval=10)

    current_index = current_index % len(media_items)
    media = media_items[current_index]
    current_index += 1

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
