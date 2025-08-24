# Matrix - Home Dashboard

## Setting Up Raspberry Pi in Kiosk Mode

Follow these steps to configure your Raspberry Pi to run Matrix in kiosk mode with chromium:

### 1. Update Your System
```bash
sudo apt update -qq
sudo apt upgrade
```

### 2. Install Required Packages
```bash
sudo apt install --no-install-recommends xserver-xorg-video-all \
  xserver-xorg-input-all xserver-xorg-core xinit x11-xserver-utils \
  chromium-browser unclutter python3-venv git
```
### 3. Clone This Repository

Clone this project repository to the Raspberry Pi:
```bash
git clone https://github.com/ianmccon/matrix.git /home/pi/matrix
```

### 4. Set Up Python Virtual Environment

Navigate to the project directory and create a virtual environment:
```bash
cd /home/pi/matrix
python -m venv venv
```

Activate the virtual environment:
```bash
source venv/bin/activate
```

Install the Python dependencies:
```bash
pip install -r requirements.txt
```

### 5. Make run.sh executable
```bash
chmod +x run.sh
```

### 6. Setup config file
```bash
cp config_matrix.json.sample config_matrix.json
```
Fill the placeholder with you details for Weather API, location, latitude, longitude and calendar .ics files

### 7. Configure autologin
```bash
sudo raspi-config
```
Go to System Options -> Auto Login
Esc -> TAB -> Finish
The pi will reboot and autologin to the console

### 8. Create /home/pi/.xinitrc
Edit or create the autostart file:
```bash
nano ~/.xinitrc
```
Add the following lines:
```bash
#!/usr/bin/env sh
xset -dpms
xset s off
xset s noblank

unclutter &
chromium-browser http://localhost:8000 \
  --window-size=1920,1080 \
  --window-position=0,0 \
  --start-fullscreen \
  --kiosk \
  --incognito \
  --noerrdialogs \
  --disable-translate \
  --no-first-run \
  --fast \
  --fast-start \
  --disable-infobars \
  --disable-features=TranslateUI \
  --disk-cache-dir=/dev/null \
  --overscroll-history-navigation=0 \
  --disable-pinch
```

### 9. Set Openbox to Start on Boot
Edit `~/.bash_profile` and add:
```bash
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    startx
fi
```

### 10. Set Up Matrix to Run on Boot

To run the Matrix application on startup, create a systemd service:

1. Create a new service file:
    ```bash
    sudo nano /etc/systemd/system/matrix.service
    ```

2. Add the following content:
    ```ini
    [Unit]
    Description=Matrix Application
    After=network.target

    [Service]
    Type=simple
    User=pi
    WorkingDirectory=/home/pi/matrix
    ExecStart=/home/pi/matrix/run.sh
    Restart=on-failure

    [Install]
    WantedBy=multi-user.target
    ```
3. Reload systemd and enable the service:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable matrix.service
    sudo systemctl start matrix.service
    ```

The Matrix application will now start automatically on boot.

### 11. Reboot
```bash
sudo reboot
```

Your Raspberry Pi should now boot directly into kiosk mode.

