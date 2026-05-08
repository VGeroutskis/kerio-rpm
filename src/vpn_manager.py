import subprocess
import shutil
import threading
import os
import time
import socket
from gi.repository import GObject, GLib

class VPNManager(GObject.Object):
    def __init__(self, container_name="keriovpn-native"):
        super().__init__()
        self._status = "unknown"
        self._is_busy = False
        self.container_name = container_name
        self._podman_path = shutil.which('podman')
        self._pkexec_path = shutil.which('pkexec')
        self._helper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vpn-helper.sh")

    def is_installed(self):
        return self._podman_path is not None

    def _run_privileged(self, cmd_type, args, capture=True):
        if not self._pkexec_path: return None
        cmd = [self._pkexec_path, self._helper_path, cmd_type] + args
        try:
            if capture:
                return subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            else:
                return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        except Exception:
            return None

    def get_status(self):
        if not self.is_installed(): return "error"
        try:
            result = self._run_privileged("podman", ["container", "inspect", "-f", "{{.State.Status}}", self.container_name])
            if result is None or result.returncode != 0: return "not_found"
            status_val = result.stdout.strip().lower()
            if status_val == "running": return "connected"
            return "disconnected"
        except Exception: return "error"

    def _get_vpn_dns(self):
        """Retrieves internal DNS server from the container's resolv.conf"""
        try:
            # We must use sudo/pkexec to exec into the root container
            res = self._run_privileged("podman", ["exec", self.container_name, "cat", "/etc/resolv.conf"])
            if res and res.stdout:
                for line in res.stdout.splitlines():
                    if line.startswith("nameserver") and "127.0.0.1" not in line and "8.8.8.8" not in line:
                        return line.split()[1]
        except: pass
        return "192.168.2.223" # Fallback to known working DNS

    def apply_custom_routes(self, routes_text):
        # 1. REMOVE HIJACKING
        res = subprocess.run(["ip", "route", "show"], capture_output=True, text=True)
        if "0.0.0.0/1" in res.stdout and "kvnet" in res.stdout:
            self._run_privileged("ip", ["route", "del", "0.0.0.0/1", "dev", "kvnet"], capture=False)
        if "128.0.0.0/1" in res.stdout and "kvnet" in res.stdout:
            self._run_privileged("ip", ["route", "del", "128.0.0.0/1", "dev", "kvnet"], capture=False)

        # 2. SETUP DNS (Automatic split-DNS)
        vpn_dns = self._get_vpn_dns()
        
        # 3. APPLY CUSTOM ROUTES
        if not routes_text: return
        routes = [r.strip() for r in routes_text.split(",") if r.strip()]
        
        for route in routes:
            try:
                # If it's a domain
                if not any(c.isdigit() for c in route):
                    # Step A: Setup split-DNS for this domain so we get the INTERNAL IP
                    # resolvectl domain kvnet ~domain.com
                    # resolvectl dns kvnet VPN_DNS_IP
                    self._run_privileged("systemctl", ["resolvectl", "dns", "kvnet", vpn_dns], capture=False)
                    self._run_privileged("systemctl", ["resolvectl", "domain", "kvnet", "~" + route], capture=False)
                    
                    # Wait for resolution to update
                    time.sleep(1)
                    
                    # Step B: Resolve the IP using the VPN DNS explicitly to be sure
                    try:
                        cmd = ["host", route, vpn_dns]
                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        target_ips = []
                        for line in res.stdout.splitlines():
                            if "has address" in line:
                                target_ips.append(line.split()[-1])
                    except:
                        continue
                else:
                    target_ips = [route]
                
                for ip in target_ips:
                    mask = "/32" if "/" not in ip else ""
                    self._run_privileged("ip", ["route", "replace", ip + mask, "via", "10.40.50.1", "dev", "kvnet"], capture=False)
            except Exception: pass

    def ensure_container_exists(self, compose_file_path=None):
        if not self.is_installed(): return False
        if compose_file_path is None:
            paths = [
                "/usr/share/kerio-rpm/docker-compose.yml",
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docker-compose.yml"),
                "./docker-compose.yml"
            ]
            for p in paths:
                if os.path.exists(p):
                    compose_file_path = p
                    break
        if not compose_file_path: return False
        try:
            if self.get_status() == "not_found":
                self._run_privileged("systemctl", ["enable", "--now", "podman.socket"], capture=False)
                self._run_privileged("podman", ["compose", "-f", compose_file_path, "up", "-d"], capture=False)
            return True
        except Exception: return False

    def connect(self, custom_routes=None):
        if self.is_installed():
            if self.get_status() != "connected":
                self._run_privileged("podman", ["start", self.container_name], capture=False)
            
            def maintenance_loop():
                for i in range(25): 
                    time.sleep(2)
                    self.apply_custom_routes(custom_routes)
                            
            threading.Thread(target=maintenance_loop, daemon=True).start()

    def disconnect(self):
        if self.is_installed():
            # Reset DNS settings for kvnet before stopping
            self._run_privileged("systemctl", ["resolvectl", "revert", "kvnet"], capture=False)
            self._run_privileged("podman", ["stop", self.container_name], capture=False)
