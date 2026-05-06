import os
import subprocess
import shutil
import threading
from gi.repository import GObject, GLib

class VPNManager(GObject.Object):
    @GObject.Property(type=str, default="unknown")
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if self._status != value:
            self._status = value
            self.notify("status")

    def __init__(self, container_name="keriovpn-native"):
        super().__init__()
        self._status = "unknown"
        self._is_busy = False
        self.container_name = container_name
        self._podman_path = shutil.which('podman')

    def is_installed(self):
        return self._podman_path is not None

    def get_status(self):
        # UI expects this method
        return self._get_status_sync()

    def _get_status_sync(self):
        if not self.is_installed():
            return "error"
        try:
            result = subprocess.run(
                [self._podman_path, "container", "inspect", "-f", "{{.State.Status}}", self.container_name],
                capture_output=True, text=True, stderr=subprocess.DEVNULL, timeout=5
            )
            if result.returncode != 0:
                return "not_found"
            status_val = result.stdout.strip().lower()
            if status_val == "running": return "connected"
            elif status_val in ["exited", "created", "stopped"]: return "disconnected"
            return "error"
        except Exception:
            return "error"

    def ensure_container_exists(self, compose_file_path=None):
        if not self.is_installed(): return False
        if self._get_status_sync() == "not_found":
            if compose_file_path is None:
                # Default search paths
                paths = [
                    "/usr/share/kerio-rpm/docker-compose.yml",
                    "./docker-compose.yml"
                ]
                for p in paths:
                    if os.path.exists(p):
                        compose_file_path = p
                        break
            
            if not compose_file_path: return False
            try:
                subprocess.run([self._podman_path, "compose", "-f", compose_file_path, "up", "-d"], timeout=60)
                return True
            except Exception: return False
        return True

    def connect(self):
        self._run_action("start")

    def disconnect(self):
        self._run_action("stop")

    def _run_action(self, action):
        if self._is_busy or not self.is_installed(): return
        self._is_busy = True
        try:
            subprocess.run([self._podman_path, action, self.container_name], timeout=30)
        except Exception: pass
        self._is_busy = False
