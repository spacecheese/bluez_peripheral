#!/usr/bin/env bash
RUN_CMD="${1:-python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m pytest tests/unit}"

DEBUG=0
while getopts ":i" opt; do
  case $opt in
    i) DEBUG=1 ;;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
  esac
done

rsync -a --progress --rsync-path="sudo rsync" \
  -e "ssh -i tests/loopback/assets/id_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2244" --delete \
  --exclude tests/loopback/assets/ \
  --exclude docs/ \
  --exclude serial.log \
  --exclude='*.venv*' \
  --exclude='*/__pycache__/*' \
  . tester@localhost:/bluez_peripheral

ssh -i tests/loopback/assets/id_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2244 -L 5678:localhost:5678 tester@localhost "
    source ~/venv/bin/activate && pip3 install debugpy && cd /bluez_peripheral && $RUN_CMD
"