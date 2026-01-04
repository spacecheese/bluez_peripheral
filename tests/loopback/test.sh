#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1}"
KEY_FILE="${2}"
PROJ_ROOT="${3}"
shift 3

INTERACTIVE=0
while getopts ":i" opt; do
  case $opt in
    i) INTERACTIVE=1 ;;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
  esac
done

SSH="ssh -i $KEY_FILE -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

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
  -e "$SSH -p 2244" --delete \
  --exclude tests/loopback/assets/ \
  --exclude docs/ \
  --exclude serial.log \
  $PROJ_ROOT tester@localhost:/bluez_peripheral

$SSH -p 2244 tester@localhost "
    set -euo pipefail

    echo '[*] Setting Up Dependencies'
    python3 -m venv ~/venv
    source ~/venv/bin/activate
    python3 -m pip install -r /bluez_peripheral/tests/requirements.txt

    sudo nohup btvirt -L -l2 >/dev/null 2>&1 &
    sudo service bluetooth start

    sudo cp /bluez_peripheral/tests/unit/com.spacecheese.test.conf /etc/dbus-1/system.d
"

if (( INTERACTIVE )); then
  $SSH -p 2244 tester@localhost || true

  wait $QEMU_PID
else
  $SSH -p 2244 tester@localhost "
    set -euo pipefail

    source ~/venv/bin/activate
    cd /bluez_peripheral
    echo '[*] Running Unit Tests'
    pytest tests/unit -s
    echo '[*] Running Loopback Tests'
    pytest tests/loopback -s
    sudo shutdown -h now
  "

  wait $QEMU_PID
fi
