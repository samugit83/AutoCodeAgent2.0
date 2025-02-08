#!/bin/bash

# 1. Clean up any old locks
rm -f /tmp/.X99-lock

# 2. Start Xvfb (virtual display) on :99
#    -ac disables access control, +extension GLX +render needed for GPU usage, etc.
Xvfb :99 -screen 0 1280x960x24 -ac +extension GLX +render -noreset &
echo "Starting Xvfb on display :99 ..."
sleep 2

# 3. (Optional) Start a simple window manager (fluxbox) for convenience
fluxbox &
echo "Fluxbox window manager started."
sleep 2

# 4. Start x11vnc to share :99 via port 5901
x11vnc \
    -display :99 \
    -rfbport 5901 \
    -forever \
    -shared \
    -nopw \
    -bg \
    -o /var/log/x11vnc.log
echo "x11vnc started on port 5901..."

# 5. Start noVNC (websockify) to proxy port 6901 => 5901
#    This will allow you to connect via browser to http://localhost:6901/vnc.html
websockify --web /usr/share/novnc/ 6901 localhost:5901 &
echo "noVNC started on port 6901..."

# 6. Start your Python app. Also set DISPLAY=:99 so that Playwright/Chromium
#    know which X server to use.
export DISPLAY=:99
echo "Starting Python app on display $DISPLAY..."
python app.py