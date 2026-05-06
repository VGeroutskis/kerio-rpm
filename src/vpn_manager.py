import subprocess

class VPNManager:
    def __init__(self, container_name="keriovpn-native"):
        self.container_name = container_name

    def is_installed(self):
        """Check if podman exists."""
        return subprocess.run(["which", "podman"], capture_output=True).returncode == 0

    def get_status(self):
        """Return status: 'connected', 'disconnected', 'error', or 'not_found'."""
        if not self.is_installed():
            return "error"
        
        result = subprocess.run(
            ["podman", "container", "inspect", "-f", "{{.State.Status}}", self.container_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            if "no such container" in result.stderr.lower():
                return "not_found"
            return "error"
            
        status = result.stdout.strip()
        if status == "running":
            return "connected"
        elif status in ["exited", "created", "paused"]:
            return "disconnected"
        else:
            return "error"

    def connect(self):
        """Start the podman container."""
        result = subprocess.run(["podman", "start", self.container_name], capture_output=True)
        return result.returncode == 0
    
    def disconnect(self):
        """Stop the podman container."""
        result = subprocess.run(["podman", "stop", self.container_name], capture_output=True)
        return result.returncode == 0
