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
        try:
            res = self._run_privileged("podman", ["exec", self.container_name, "cat", "/etc/resolv.conf"])
            if res and res.stdout:
                for line in res.stdout.splitlines():
                    if line.startswith("nameserver") and "127.0.0.1" not in line and "8.8.8.8" not in line:
                        return line.split()[1]
        except: pass
        return "192.168.2.223"

    def apply_custom_routes(self, routes_text):
        # 1. MTU FIX
        self._run_privileged("ip", ["link", "set", "dev", "kvnet", "mtu", "1300"], capture=False)

        # 2. REMOVE HIJACKING
        res = subprocess.run(["ip", "route", "show"], capture_output=True, text=True)
        if "0.0.0.0/1" in res.stdout and "kvnet" in res.stdout:
            self._run_privileged("ip", ["route", "del", "0.0.0.0/1", "dev", "kvnet"], capture=False)
        if "128.0.0.0/1" in res.stdout and "kvnet" in res.stdout:
            self._run_privileged("ip", ["route", "del", "128.0.0.0/1", "dev", "kvnet"], capture=False)

        # 3. DNS SETUP
        vpn_dns = self._get_vpn_dns()
        self._run_privileged("systemctl", ["resolvectl", "dns", "kvnet", vpn_dns], capture=False)
        
        if not routes_text: return
        
        # 4. PARSE ROUTES
        routes = routes_text.replace(",", " ").split()
        
        # We need to collect all domains to set them all at once in resolvectl
        # because calling it multiple times overwrites the previous settings.
        domain_list = []
        for route in routes:
            route = route.strip()
            if not route: continue
            
            try:
                if not any(c.isdigit() for c in route):
                    # It's a domain
                    domain_list.append(route)
                    domain_list.append("~" + route) # Add routing mark
                    
                    # Resolve IP for this domain using VPN DNS
                    try:
                        cmd = ["host", route, vpn_dns]
                        lookup = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        for line in lookup.stdout.splitlines():
                            if "has address" in line:
                                ip = line.split()[-1]
                                self._run_privileged("ip", ["route", "replace", ip + "/32", "via", "10.40.50.1", "dev", "kvnet"], capture=False)
                    except: pass
                else:
                    # It's an IP
                    target = route if "/" in route else route + "/32"
                    self._run_privileged("ip", ["route", "replace", target, "via", "10.40.50.1", "dev", "kvnet"], capture=False)
            except Exception: pass

        # Apply ALL domains at once
        if domain_list:
            self._run_privileged("systemctl", ["resolvectl", "domain", "kvnet"] + domain_list, capture=False)

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
                for i in range(30): 
                    time.sleep(2)
                    self.apply_custom_routes(custom_routes)
                            
            threading.Thread(target=maintenance_loop, daemon=True).start()

    def disconnect(self):
        if self.is_installed():
            self._run_privileged("systemctl", ["resolvectl", "revert", "kvnet"], capture=False)
            self._run_privileged("podman", ["stop", self.container_name], capture=False)
