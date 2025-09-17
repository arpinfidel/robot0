# robot0

Motor control service for a Raspberry Pi. The app exposes a FastAPI WebSocket endpoint that drives the left and right motors via GPIO.

## Requirements
- Raspberry Pi OS (or other Debian-based distro with `systemd`)
- Python 3.10+
- GPIO access (`RPi.GPIO` requires running on a Pi)

## Setup
1. Clone or copy the repository onto the Pi.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the service manually
With the virtual environment activated, start the FastAPI server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
This exposes the WebSocket endpoint at `ws://<pi-ip>:8000/ws`. Use `Ctrl+C` to stop the service.

> Tip: `python main.py` is equivalent and uses the same configuration.

## Running on boot with systemd
1. Create a service definition at `/etc/systemd/system/robot0.service` (adjust `User`, `WorkingDirectory`, and the virtualenv path as needed):
   ```ini
   [Unit]
   Description=robot0 FastAPI motor control service
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/robot0
   ExecStart=/home/pi/robot0/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```
2. Reload `systemd` and enable the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now robot0.service
   ```
3. Check status and logs when needed:
   ```bash
   systemctl status robot0.service
   sudo journalctl -u robot0.service -f
   ```

Disabling the service later:
```bash
sudo systemctl disable --now robot0.service
```
