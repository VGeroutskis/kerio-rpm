import gi
import os
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
from vpn_manager import VPNManager
from config_handler import ConfigHandler
import multiprocessing
import threading

from tray import tray_main

class SettingsWindow(Adw.Window):
    def __init__(self, parent, config_handler, on_save_callback):
        super().__init__(transient_for=parent, modal=True)
        self.set_title("VPN Settings")
        self.set_default_size(350, 250)
        
        self.config_handler = config_handler
        self.on_save_callback = on_save_callback
        
        config = self.config_handler.load()
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        self.set_content(box)
        
        # Form
        group = Adw.PreferencesGroup()
        box.append(group)
        
        self.server_entry = Adw.EntryRow(title="Server")
        self.server_entry.set_text(config["server"])
        group.add(self.server_entry)
        
        self.port_entry = Adw.EntryRow(title="Port")
        self.port_entry.set_text(config["port"])
        group.add(self.port_entry)
        
        self.username_entry = Adw.EntryRow(title="Username")
        self.username_entry.set_text(config["username"])
        group.add(self.username_entry)
        
        self.password_entry = Adw.PasswordEntryRow(title="Password")
        self.password_entry.set_text(config["password"])
        group.add(self.password_entry)
        
        save_button = Gtk.Button(label="Save", halign=Gtk.Align.CENTER)
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self.on_save_clicked)
        box.append(save_button)
        
    def on_save_clicked(self, button):
        server = self.server_entry.get_text()
        port = self.port_entry.get_text()
        username = self.username_entry.get_text()
        password = self.password_entry.get_text()
        
        self.config_handler.save(server, port, username, password)
        self.on_save_callback()
        self.close()

class KerioWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Kerio VPN")
        self.set_default_size(400, 300)

        self.vpn_manager = VPNManager()
        self.vpn_manager.connect("notify::status", self.on_vpn_status_changed)
        
        self.config_handler = ConfigHandler()
        self.compose_path = "/usr/share/kerio-rpm/docker-compose.yml"
        if not os.path.exists(self.compose_path):
            # Fallback for dev: check current directory and project root
            if os.path.exists("docker-compose.yml"):
                self.compose_path = os.path.abspath("docker-compose.yml")
            elif os.path.exists("../docker-compose.yml"):
                self.compose_path = os.path.abspath("../docker-compose.yml")

        # Minimize to Tray setting
        self.minimize_to_tray = True
        self.connect("close-request", self.on_close_request)

        # Layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        # Header Bar
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)

        # Settings button
        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.connect("clicked", lambda x: self.show_settings())
        self.header.pack_start(settings_btn)

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

    def show_settings(self):
        settings = SettingsWindow(self, self.config_handler, self.on_settings_saved)
        settings.present()
        
    def on_settings_saved(self):
        # After saving settings, call vpn_manager.ensure_container_exists()
        def _ensure():
            self.vpn_manager.ensure_container_exists(self.compose_path)
            
        threading.Thread(target=_ensure, daemon=True).start()
        self.present()

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
            self.status_page.set_description(f"Container '{self.vpn_manager.container_name}' does not exist")
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
            
        # First Run Check
        config_path = os.path.expanduser("~/.config/kerio-rpm/kerio-kvc.conf")
        if not os.path.exists(config_path):
            win.show_settings()
        else:
            win.present()
            
        # Push initial status
        self.status_queue.put(win.vpn_manager.status)
