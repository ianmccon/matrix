#!/bin/bash

#####  Updating repos
sudo apt update -y

#####  Installing ZSH
sudo apt install zsh -y

#####  Installing Oh-my-zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

#####  Updating Theme
sed -i 's/ZSH_THEME="robbyrussel"/ZSH_THEME="bira"/gi' ~/.zshrc
source  ~/.zshrc

#####  Install chromium
sudo apt install chromium-browser unclutter -y


#####  Configure .xinitrc for autostart
mkdir ~/.config/labwc
nano ~/.config/labwc/autostart

#!/bin/bash
xset s off # Disable screen saver
xset -dpms # Disable power management
xset s noblank # Prevent screen blanking
openbox-session & # Start Openbox window manager
chromium-browser --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble --disable-features=TranslateUI http://localhost:8000


chmod +x ~/.xinitrc 

### Set up shares
sudo mkdir /mnt/backups
sudo mkdir /mnt/data

### Edit /etc/fstab to automount shares
sudo nano /etc/fstab
## Add the following lines to the end of the file
//192.168.86.200/Backups /mnt/backups cifs username=<user>,password=<password>,uid=pi,gid=pi 0 0
//192.168.86.200/Data /mnt/data cifs username=<user>,password=<password>,uid=pi,gid=pi 0 0

sudo systemctl daemon-reload
sudo mount -a

### Setup Github SSH keys
ssh-keygen -t ed25519 -C "ian@ianmcconachie.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
### Copy the above key to Github

### Clone Matrix repo
git clone git@github.com:ianmccon/matrix.git
git clone git@github.com:ianmccon/mediastack.git

sudo nano /etc/systemd/system/matrix.service

[Unit]
Description=Matrix
After=network.target

[Service]
User=pi
ExecStart=/home/pi/matrix/run.sh
Restart=always

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable matrix.service
sudo systemctl start matrix.service



