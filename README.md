# Digital Picture Frame Solution

## Overview

I have created a digital picture frame application that:

- Runs inside a Docker container on my Linux workstation.
- Serves a slideshow of images and videos over my local network.
- Provides an admin interface to upload and delete media.
- Stores media and a SQLite database on a mounted USB stick for persistence.
- Uses a Python/Flask backend with the Waitress WSGI server.
- Automatically restarts on system reboot and remains accessible to devices on the same LAN.
- Dynamically determines and stores video lengths, ensuring each video plays fully before moving on.

## Motivation and Setup

I wanted a way to display family photos and videos on digital picture frames around my home, but I found most commercially available solutions to be expensive, have poor user interfaces, and offer very limited customization. Instead, I purchased two affordable Android tablets, placed them into picture frames, and mounted them on the wall. I configured these tablets to:

- Run in full kiosk mode, showing only the slideshow webpage.
- Use their front camera to detect motion and turn on the display automatically when someone approaches.
- Offload all heavy logic and data management to the backend, leaving a minimal overhead on the front end, thus conserving battery and resources.
  
This approach gives me a highly customizable, private, and cost-effective digital picture frame setup. At roughly half the price of commercial frames, I get better performance and more features. I can easily upload or remove media from my phone or computer’s browser, as long as I’m on the same secure home network.

## Key Features

1. **Slideshow Display**:  
   I developed a simple web page (`/display`) that shows images and videos one at a time. Images cycle through at a fixed interval, while videos are fully played regardless of length. After a video finishes, the page refreshes to the next media item.

2. **Admin Interface**:  
   I implemented a password-protected `/admin` page where I can:
   - Upload new images (JPG, PNG) and videos (MP4, MOV).
   - Automatically generate thumbnails for easy visual reference.
   - Delete unwanted media quickly and easily.

3. **Dynamic Video Duration Handling**:  
   When I upload a video, the backend uses `ffprobe` to determine its exact duration. It stores this duration in the database along with other metadata. During playback, the slideshow logic uses this stored duration to calculate how long to display the video before automatically transitioning to the next media item. This ensures perfect video playback timing without guesswork or hardcoded intervals.

4. **Local File Storage and Persistence**:  
   I store all media files and the `db.sqlite3` database on a USB stick mounted into the Docker container at runtime. This setup guarantees persistence across container restarts and simplifies backups and portability.

5. **Dockerized Deployment**:  
   By running everything inside a Docker container, I ensure a controlled, reproducible environment. Waitress serves the Flask app, providing a stable production-grade server environment.

6. **Local Network Access Only**:  
   I configured my firewall and network so that the service is only accessible on my LAN. My tablets, phone, and computer—all connected to the same network—can access the slideshow and admin page. There’s no exposure to the public internet, keeping my family media private.

7. **Automatic Startup on Reboot**:  
   By using Docker’s `--restart=unless-stopped` policy, the container and thus the digital picture frame service automatically start on system reboot, ensuring a hands-off, always-available setup.

## Steps I Took

1. **Initial Application Setup**:
   - Created a Flask app to display media at `/display` and administer media at `/admin`.
   - Implemented file uploads for images and videos.
   - Integrated thumbnail generation using Pillow for images and ffmpeg for videos.
   - Added authentication to the admin dashboard to prevent unauthorized access.

2. **Refactoring and Packaging**:
   - Organized code into an `app` directory with `__init__.py`, `app.py`, and `models.py`.
   - Used `from app.models import ...` so Waitress can run `app.app:app` smoothly.

3. **Database and Session Management**:
   - Employed SQLAlchemy and a scoped session with `teardown_appcontext` to ensure sessions are cleaned up after each request.
   - Stored the database file (`db.sqlite3`) and media files outside the container (on the USB stick), mounting them as volumes at runtime.

4. **Dockerization**:
   - Authored a `Dockerfile` that installs Python dependencies, ffmpeg, and runs Waitress as the WSGI server.
   - Kept media and database outside the image, mounting them at runtime for persistence.

5. **Networking and Firewall**:
   - Ensured my Linux workstation is on the same LAN as my devices (using bridging if necessary).
   - Adjusted firewall rules to allow inbound traffic on port 8080 from the LAN only.

6. **Permissions and Ownership**:
   - Granted appropriate file permissions (e.g., `chmod 666` for db.sqlite3 and `chmod 777` for media directories) so that the container can read and write data seamlessly.

7. **Automatic Restart**:
   - Launched the container with `--restart=unless-stopped` to automatically restart after system reboots and run continuously without manual intervention.

Yes, if you're already hosting the Docker image on a public registry like Docker Hub, others can skip the build and push steps. You can simplify the usage instructions as follows:


## Usage Instructions

1. **Pull the Docker Image**:  
   Instead of building the image locally, simply pull it from my Docker Repo:
   ```bash
   docker pull panog/pictureframe:latest
   ```

2. **Prepare Host Directories**:
   ```bash
   sudo mkdir -p /mnt/usb/pictureframe_data/media/thumbnails
   sudo touch /mnt/usb/pictureframe_data/db.sqlite3
   sudo chmod 777 /mnt/usb/pictureframe_data/media
   sudo chmod 777 /mnt/usb/pictureframe_data/media/thumbnails
   sudo chmod 666 /mnt/usb/pictureframe_data/db.sqlite3
   ```

3. **Run the Container**:
   ```bash
   docker run -d --name pictureframe \
     --restart=unless-stopped \
     -p 8080:8080 \
     -v /mnt/usb/pictureframe_data/media:/app/app/media \
     -v /mnt/usb/pictureframe_data/db.sqlite3:/app/app/db.sqlite3 \
     panog/pictureframe:latest
   ```

4. **Access the Application**:
   - Determine your Linux workstation’s IP on the LAN (e.g., `192.168.1.20`).
   - From another device on the LAN:
     - Slideshow: `http://192.168.1.20:8080/display`
     - Admin: `http://192.168.1.20:8080/admin`

## Conclusion

By following these steps, I’ve created a feature-rich, stable, and customizable digital picture frame solution at a fraction of the cost of commercial options. My Android tablets, set in kiosk mode and mounted on the wall, detect motion via their front cameras and display family images and videos only when someone is nearby—conserving battery and running minimal code on the frontend. The backend dynamically calculates video durations at upload time, ensuring flawless autoplay without additional overhead. I can easily manage media from my phone or computer’s browser, making this solution more flexible, private, and economical than off-the-shelf digital frames.

## Authorship and License

**Author:** Panagiotis Georgiadis

**Copyright:**  
© Panagiotis Georgiadis. All rights reserved.

Any unauthorized use or distribution of this project’s code or concepts is strictly prohibited.

For inquiries about usage, permissions, or contributions, please contact me directly.