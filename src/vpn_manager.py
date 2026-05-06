import subprocess
import shutil

class VPNManager:
    def __init__(self, container_name="keriovpn-native"):
        self.container_name = container_name
        self._podman_path = shutil.which('podman')

    def is_installed(self):
        """Check if podman exists."""
        return self._podman_path is not None

    def get_status(self):
        """Return status: 'connected', 'disconnected', 'paused', 'not_found', or 'error'."""
        if not self.is_installed():
            return "error"
        
        try:
            result = subprocess.run(
                [self._podman_path, "container", "inspect", "-f", "{{.State.Status}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                if "no such container" in result.stderr.lower():
                    return "not_found"
                return "error"
                
            status = result.stdout.strip().lower()
            if status == "running":
                return "connected"
            elif status == "paused":
                return "paused"
            elif status in ["exited", "created", "stopped"]:
                return "disconnected"
            elif status in ["restarting", "removing"]:
                return "transitioning"
            else:
                return "error"
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return "error"

    def connect(self):
        """Start the podman container."""
        if not self.is_installed():
            return False
        try:
            result = subprocess.run(
                [self._podman_path, "start", self.container_name], 
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def disconnect(self):
        """Stop the podman container."""
        if not self.is_installed():
            return False
        try:
            result = subprocess.run(
                [self._podman_path, "stop", self.container_name], 
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
