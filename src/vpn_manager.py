import subprocess
import shutil
import threading
import os
from gi.repository import GObject, GLib

class VPNManager(GObject.Object):
    def __init__(self, container_name="keriovpn-native"):
        super().__init__()
        self._status = "unknown"
        self._is_busy = False
        self.container_name = container_name
        self._podman_path = shutil.which('podman')

    def is_installed(self):
        return self._podman_path is not None

    def get_status(self):
        if not self.is_installed(): return "error"
        try:
            result = subprocess.run(
                [self._podman_path, "container", "inspect", "-f", "{{.State.Status}}", self.container_name],
                capture_output=True, text=True, stderr=subprocess.DEVNULL, timeout=5
            )
            if result.returncode != 0: return "not_found"
            status_val = result.stdout.strip().lower()
            if status_val == "running": return "connected"
            return "disconnected"
        except Exception: return "error"

    def ensure_container_exists(self, compose_file_path=None):
        if not self.is_installed(): return False
        
        # Determine compose file path
        if compose_file_path is None:
            # Try RPM path first, then local dev path
            paths = [
                "/usr/share/kerio-rpm/docker-compose.yml",
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml"),
                "./docker-compose.yml"
            ]
            for p in paths:
                if os.path.exists(p):
                    compose_file_path = p
                    break
        
        if not compose_file_path: return False
        
        # Run podman compose up
        try:
            # First, check if already exists to avoid unnecessary pull
            if self.get_status() == "not_found":
                subprocess.run([self._podman_path, "compose", "-f", compose_file_path, "up", "-d"], timeout=120)
            return True
        except Exception: return False

    def connect(self):
        if self.is_installed():
            subprocess.run([self._podman_path, "start", self.container_name], stderr=subprocess.DEVNULL)

    def disconnect(self):
        if self.is_installed():
            subprocess.run([self._podman_path, "stop", self.container_name], stderr=subprocess.DEVNULL)
