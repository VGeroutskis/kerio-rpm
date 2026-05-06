import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
from vpn_manager import VPNManager
import multiprocessing
import threading

from tray import tray_main

class KerioWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Kerio VPN")
        self.set_default_size(400, 300)

        self.vpn_manager = VPNManager()
        self.vpn_manager.connect("notify::status", self.on_vpn_status_changed)
        
        # Minimize to Tray setting
        self.minimize_to_tray = True
        self.connect("close-request", self.on_close_request)

        # Layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        # Header Bar
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)

        # Status Page
        self.status_page = Adw.StatusPage(
            title="Checking...",
            description="Detecting VPN status",
            icon_name="network-vpn-symbolic"
        )
        self.main_box.append(self.status_page)

        # Connection Switch
        self.switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.switch.connect("state-set", self.on_switch_state_set)
        
        # Add switch to header
        self.header.pack_end(self.switch)

        # Start polling via VPNManager
        self.vpn_manager.start_polling(interval_seconds=2)
        self.connect("destroy", self.on_destroy)

    def on_close_request(self, *args):
        if self.minimize_to_tray:
            self.hide()
            return True
        return False

    def on_vpn_status_changed(self, manager, pspec):
        status = manager.status
        GLib.idle_add(self.update_ui, status)
        # Push to tray
        app = self.get_application()
        if app and hasattr(app, 'status_queue'):
            app.status_queue.put(status)

    def update_ui(self, status):
        # UI Responsiveness: Disable switch during transitions
        self.switch.set_sensitive(status != "transitioning")
        
        if status == "connected":
            self.status_page.set_title("Connected")
            self.status_page.set_description("VPN is active")
            self.switch.set_active(True)
        elif status == "disconnected":
            self.status_page.set_title("Disconnected")
            self.status_page.set_description("VPN is inactive")
            self.switch.set_active(False)
        elif status == "not_found":
            self.status_page.set_title("Container Not Found")
            self.status_page.set_description("Container 'keriovpn-native' does not exist")
            self.switch.set_active(False)
        elif status == "transitioning":
            self.status_page.set_title("Transitioning...")
            self.status_page.set_description("Container is changing state")
        else:
            self.status_page.set_title("Error")
            self.status_page.set_description(f"Status: {status}")
            self.switch.set_active(False)
        return False

    def on_switch_state_set(self, switch, state):
        # Async VPN Calls: These methods now run in threads
        if state:
            self.vpn_manager.connect()
        else:
            self.vpn_manager.disconnect()
        return True # Handled asynchronously

    def on_destroy(self, *args):
        # Cleanup: Stop polling via VPNManager when window is destroyed
        self.vpn_manager.stop_polling()

class KerioApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.kerio_rpm",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        # Initialize queues for tray communication
        ctx = multiprocessing.get_context('spawn')
        self.status_queue = ctx.Queue()
        self.cmd_queue = ctx.Queue()
        self.tray_process = None

    def do_startup(self):
        super().do_startup()
        # Start tray process
        ctx = multiprocessing.get_context('spawn')
        self.tray_process = ctx.Process(
            target=tray_main, 
            args=(self.status_queue, self.cmd_queue),
            daemon=True
        )
        self.tray_process.start()
        
        # Start command listener
        thread = threading.Thread(target=self.listen_cmd, daemon=True)
        thread.start()

    def listen_cmd(self):
        while True:
            try:
                cmd = self.cmd_queue.get()
                GLib.idle_add(self.handle_cmd, cmd)
            except Exception:
                break
            
    def handle_cmd(self, cmd):
        windows = self.get_windows()
        win = windows[0] if windows else None
        
        if cmd == "show":
            if win: win.present()
        elif cmd == "hide":
            if win: win.hide()
        elif cmd == "connect":
            if win: win.vpn_manager.connect()
        elif cmd == "disconnect":
            if win: win.vpn_manager.disconnect()
        elif cmd == "quit":
            self.quit()

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            win = KerioWindow(application=self)
        win.present()
        # Push initial status
        self.status_queue.put(win.vpn_manager.status)
