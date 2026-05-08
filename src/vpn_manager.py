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

    def _resolve_domain(self, domain):
        """Resolves a domain to all its IPv4 addresses, including www subdomain"""
        ips = set()
        domains_to_try = [domain]
        if not domain.startswith("www."):
            domains_to_try.append("www." + domain)
            
        for d in domains_to_try:
            try:
                info = socket.getaddrinfo(d, None, socket.AF_INET)
                for item in info:
                    ips.add(item[4][0])
            except:
                pass
        return list(ips)

    def apply_custom_routes(self, routes_text):
        # 1. REMOVE HIJACKING ROUTES (0.0.0.0/1 and 128.0.0.0/1)
        res = subprocess.run(["ip", "route", "show"], capture_output=True, text=True)
        if "0.0.0.0/1" in res.stdout and "kvnet" in res.stdout:
            self._run_privileged("ip", ["route", "del", "0.0.0.0/1", "dev", "kvnet"], capture=False)
        if "128.0.0.0/1" in res.stdout and "kvnet" in res.stdout:
            self._run_privileged("ip", ["route", "del", "128.0.0.0/1", "dev", "kvnet"], capture=False)

        # 2. APPLY CUSTOM ROUTES
        if not routes_text: return
        routes = [r.strip() for r in routes_text.split(",") if r.strip()]
        
        # Get current routing table to avoid redundant calls
        current_routes = subprocess.run(["ip", "route", "show"], capture_output=True, text=True).stdout

        for route in routes:
            try:
                if route.lower() in ["all", "everything", "0.0.0.0/0"]:
                    if "0.0.0.0/1 via 10.40.50.1" not in current_routes:
                        self._run_privileged("ip", ["route", "replace", "0.0.0.0/1", "via", "10.40.50.1", "dev", "kvnet"], capture=False)
                    if "128.0.0.0/1 via 10.40.50.1" not in current_routes:
                        self._run_privileged("ip", ["route", "replace", "128.0.0.0/1", "via", "10.40.50.1", "dev", "kvnet"], capture=False)
                    continue

                target_ips = []
                if not any(c.isdigit() for c in route):
                    target_ips = self._resolve_domain(route)
                else:
                    target_ips = [route]
                
                for ip in target_ips:
                    mask = "/32" if "/" not in ip else ""
                    full_target = ip + mask
                    if f"{full_target} via 10.40.50.1" not in current_routes:
                        self._run_privileged("ip", ["route", "replace", full_target, "via", "10.40.50.1", "dev", "kvnet"], capture=False)
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
                # Aggressive fighting for the first minute
                for i in range(30): 
                    time.sleep(2)
                    self.apply_custom_routes(custom_routes)
                            
            threading.Thread(target=maintenance_loop, daemon=True).start()

    def disconnect(self):
        if self.is_installed():
            self._run_privileged("podman", ["stop", self.container_name], capture=False)
