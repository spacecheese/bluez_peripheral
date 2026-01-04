PYTHON_ARGS="-m pytest tests/unit"
ssh -i tests/loopback/assets/id_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2244 -L 5678:localhost:5678 tester@localhost "
    source ~/venv/bin/activate && pip3 install debugpy && cd /bluez_peripheral && python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client $PYTHON_ARGS
"