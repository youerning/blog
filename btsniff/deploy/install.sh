#!/usr/bin/env bash
# Run on the server after the project has been copied to /opt/bt-sniff.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

sudo mkdir -p /opt/bt-sniff /var/lib/bt-sniff
sudo chown -R "$(id -un):$(id -gn)" /opt/bt-sniff /var/lib/bt-sniff

cd /opt/bt-sniff
uv sync
if [ ! -f config.toml ]; then
    cp config.example.toml config.toml
    echo "created config.toml - set harvest.self_ip to this machine's public IP"
fi

sudo cp deploy/bt-sniff.service /etc/systemd/system/bt-sniff.service
sudo systemctl daemon-reload
sudo systemctl enable --now bt-sniff

# Make the CLI usable from anywhere (config lookup + short wrapper).
sudo mkdir -p /etc/bt-sniff
sudo ln -sf /opt/bt-sniff/config.toml /etc/bt-sniff/config.toml
printf '#!/bin/sh\nexec /opt/bt-sniff/.venv/bin/bt-sniff "$@"\n' | sudo tee /usr/local/bin/sniff >/dev/null
sudo chmod +x /usr/local/bin/sniff

for rule in "6881/udp bt-sniff-dht" "6882/tcp bt-sniff-peers" "6882/udp bt-sniff-utp"; do
    set -- $rule
    sudo ufw allow "$1" comment "$2" >/dev/null 2>&1 || true
done

echo "installed. check: journalctl -fu bt-sniff"
