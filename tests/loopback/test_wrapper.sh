wget -O id_ed25519 https://github.com/spacecheese/bluez_images/releases/download/0.0.13/id_ed25519
wget -O image.qcow2 https://github.com/spacecheese/bluez_images/releases/download/0.0.13/ubuntu-24.04-bluez-5.66.qcow2


chmod 600 id_ed25519
./test.sh image.qcow2