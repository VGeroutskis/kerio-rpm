import subprocess
import shutil
import threading
from gi.repository import GObject, GLib

class VPNManager(GObject.Object):
    _status = "unknown"
    _is_busy = False
    _refreshing = False
    _timeout_id = None

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
        self.container_name = container_name
        self._podman_path = shutil.which('podman')

    def is_installed(self):
        """Check if podman exists."""
        return self._podman_path is not None

    def start_polling(self, interval_seconds=2):
        """Starts periodic status polling."""
        if self._timeout_id is None:
            self._timeout_id = GLib.timeout_add_seconds(interval_seconds, self.refresh_status)
            self.refresh_status()

    def stop_polling(self):
        """Stops periodic status polling."""
        if self._timeout_id is not None:
            GLib.Source.remove(self._timeout_id)
            self._timeout_id = None

    def refresh_status(self):
        """Update status asynchronously. Returns True to keep timeout alive."""
        if self._is_busy or self._refreshing or not self.is_installed():
            if not self.is_installed():
                self.status = "error"
            return True
            
        self._refreshing = True
        def _task():
            new_status = self._get_status_sync()
            GLib.idle_add(self._set_status, new_status)

        threading.Thread(target=_task, daemon=True).start()
        return True

    def _set_status(self, new_status):
        self._refreshing = False
        self.status = new_status
        return False

    def _get_status_sync(self):
        """Synchronous status check (to be run in a thread)."""
        if not self.is_installed():
            return "error"
            
        try:
            result = subprocess.run(
                [self._podman_path, "container", "inspect", "-f", "{{.State.Status}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                stderr = result.stderr.lower()
                if "no such container" in stderr or "error: no such" in stderr:
                    return "not_found"
                return "error"
                
            status_val = result.stdout.strip().lower()
            if status_val == "running":
                return "connected"
            elif status_val == "paused":
                return "paused"
            elif status_val in ["exited", "created", "stopped"]:
                return "disconnected"
            elif status_val in ["restarting", "removing"]:
                return "transitioning"
            else:
                return "error"
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return "error"

    def ensure_container_exists(self, compose_file_path):
        """Runs podman compose -f <path> up -d if the container is missing."""
        if not self.is_installed():
            return False
            
        status = self._get_status_sync()
        if status == "not_found":
            try:
                subprocess.run(
                    [self._podman_path, "compose", "-f", compose_file_path, "up", "-d"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                self.refresh_status()
                return True
            except Exception:
                return False
        return True

    def connect(self):
        """Start the podman container asynchronously."""
        self._run_action_async("start")

    def disconnect(self):
        """Stop the podman container asynchronously."""
        self._run_action_async("stop")

    def _run_action_async(self, action):
        if self._is_busy or not self.is_installed():
            return

        self._is_busy = True
        self.status = "transitioning"
        
        def _task():
            try:
                subprocess.run(
                    [self._podman_path, action, self.container_name], 
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            except Exception:
                pass
            
            GLib.idle_add(self._on_action_finished)

        threading.Thread(target=_task, daemon=True).start()

    def _on_action_finished(self):
        self._is_busy = False
        self.refresh_status()
        return False
