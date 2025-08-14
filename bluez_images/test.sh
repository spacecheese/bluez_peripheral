#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1}"

SSH="ssh -i id_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "[*] Starting QEMU session"
qemu-system-x86_64 \
    -m 2048 \
    -smp 2 \
    -nographic \
    -drive file="$IMAGE",format=qcow2 \
    -netdev user,id=net0,hostfwd=tcp::2244-:22 \
    -device virtio-net-pci,netdev=net0 \
    -no-reboot \
    -monitor none \
    -display none \
    -serial file:"serial.log" &

QEMU_PID=$!
kill_qemu() {
  if kill -0 $QEMU_PID 2>/dev/null; then
    echo "[!] Killing QEMU"
    kill $QEMU_PID 2>/dev/null || true
  fi
}
trap kill_qemu EXIT

SSH_UP=0
for i in {1..30}; do
    echo "[*] Waiting for SSH..."
    if $SSH -p 2244 tester@localhost 'true'; then
        echo "[✓] SSH Connected"
        SSH_UP=1
        break
    fi
    sleep 5
done

if [[ $SSH_UP -ne 1 ]]; then
    echo "[✗] SSH Connection Timed Out"
    exit 1
fi

echo "[*] Copying bluez_peripheral"
rsync -a --progress --rsync-path="sudo rsync" \
  -e "$SSH -p 2244" --exclude bluez_images \
  "../" tester@localhost:/bluez_peripheral

echo "[*] Testing adapter"
$SSH -p 2244 tester@localhost "
    python3 -m venv ~/venv
    source ~/venv/bin/activate
    pip install -r /bluez_peripheral/tests/requirements.txt

    sudo nohup btvirt -L -l2 >/dev/null 2>&1 &
    sudo service bluetooth start

    cd /bluez_peripheral
    python3 -m tests.test
    sudo shutdown -h now
"
wait $QEMU_PID
