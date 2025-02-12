#!/bin/bash

rm -f /tmp/.X99-lock

Xvfb :99 -screen 0 1280x960x24 -ac +extension GLX +render -noreset &
echo "Starting Xvfb on display :99 ..."
sleep 2

fluxbox &
echo "Fluxbox window manager started."
sleep 2

x11vnc \
    -display :99 \
    -rfbport 5901 \
    -forever \
    -shared \
    -nopw \
    -bg \
    -o /var/log/x11vnc.log
echo "x11vnc started on port 5901..."

websockify --web /usr/share/novnc/ 6901 localhost:5901 &
echo "noVNC started on port 6901..."

export DISPLAY=:99
echo "Starting Python app on display $DISPLAY..."
python app.py