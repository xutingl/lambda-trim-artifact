#!/bin/bash

SILENT="-qq -o=Dpkg::Use-Pty=0"

# Update the package list in quiet mode
echo "[+] Updating the package list..."
sudo apt-get update $SILENT
echo "[+] Package list updated successfully."

# install Access Control List (ACL) package and systemd-nspawn
sudo apt-get $SILENT install -y acl systemd-container

# ----------------- Install Python3.10 -------------------
echo "[+] Installing Python 3.10..."
sudo apt-get install $SILENT -y python3.10 python3.10-dev python3.10-venv
echo "[+] Python 3.10 installed successfully."
# ---------------------------------------------------------

# ----------------- Install Docker -------------------
echo "[+] Installing Docker..."
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
echo "[+] Docker installed successfully."
# ---------------------------------------------------------

# ----------------- Install AWS CLI -------------------
echo "[+] Installing AWS..."
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

rm awscliv2.zip
echo "[+] AWS CLI installed successfully."
# ---------------------------------------------------------
