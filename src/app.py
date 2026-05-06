import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
import os
import threading
from config_handler import ConfigHandler
from vpn_manager import VPNManager
from multiprocessing import Process, Queue

class SettingsWindow(Adw.Window):
    def __init__(self, parent, config_handler, vpn_manager, **kwargs):
        super().__init__(transient_for=parent, modal=True, **kwargs)
        self.config_handler = config_handler
        self.vpn_manager = vpn_manager
        self.set_title("Kerio VPN Settings")
        self.set_default_size(400, 300)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        self.set_content(box)

        # Form fields
        self.server_entry = Gtk.Entry(placeholder_text="VPN Server IP/Hostname")
        self.user_entry = Gtk.Entry(placeholder_text="Username")
        self.pass_entry = Gtk.Entry(placeholder_text="Password", visibility=False)
        self.fp_entry = Gtk.Entry(placeholder_text="MD5 Fingerprint")

        box.append(Gtk.Label(label="Connection Settings", css_classes=["title-4"]))
        box.append(self.server_entry)
        box.append(self.user_entry)
        box.append(self.pass_entry)
        
        fp_box = Gtk.Box(spacing=6)
        fp_box.append(self.fp_entry)
        self.fp_entry.set_hexpand(True)
        fetch_btn = Gtk.Button(label="Fetch")
        fetch_btn.connect("clicked", self.on_fetch_clicked)
        fp_box.append(fetch_btn)
        box.append(fp_box)

        save_btn = Gtk.Button(label="Save and Setup Container", css_classes=["suggested-action"])
        save_btn.connect("clicked", self.on_save_clicked)
        box.append(save_btn)

        # Load current config if exists
        config = self.config_handler.load_config()
        if config:
            self.server_entry.set_text(config.get('server', ''))
            self.user_entry.set_text(config.get('username', ''))
            self.fp_entry.set_text(config.get('fingerprint', ''))

    def on_fetch_clicked(self, btn):
        server = self.server_entry.get_text()
        if server:
            # Simple sync call for fingerprint
            import subprocess
            try:
                cmd = f"openssl s_client -connect {server}:4090 < /dev/null 2>/dev/null | openssl x509 -fingerprint -md5 -noout | sed 's/.*=//'"
                fp = subprocess.check_output(cmd, shell=True, text=True).strip()
                self.fp_entry.set_text(fp)
            except:
                pass

    def on_save_clicked(self, btn):
        self.config_handler.save_config(
            server=self.server_entry.get_text(),
            username=self.user_entry.get_text(),
            password=self.pass_entry.get_text(),
            fingerprint=self.fp_entry.get_text()
        )
        # Run compose in background
        threading.Thread(target=self.vpn_manager.ensure_container_exists, daemon=True).start()
        self.close()

class KerioWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Kerio VPN")
        self.set_default_size(450, 400)
        self.vpn_manager = VPNManager()
        self.config_handler = ConfigHandler()

        # UI Elements
        self.status_page = Adw.StatusPage(title="Disconnected", icon_name="network-vpn-disabled-symbolic")
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_top(30)
        main_box.append(self.status_page)

        self.connect_switch = Gtk.Switch()
        self.connect_switch.set_halign(Gtk.Align.CENTER)
        self.connect_switch.connect("state-set", self.on_switch_state_set)
        main_box.append(self.connect_switch)

        settings_btn = Gtk.Button(label="Settings", halign=Gtk.Align.CENTER)
        settings_btn.connect("clicked", self.on_settings_clicked)
        main_box.append(settings_btn)

        self.set_content(main_box)

        # Status Update Timer
        self.timeout_id = GLib.timeout_add_seconds(2, self.update_ui_status)
        self.connect("destroy", self.on_destroy)
        
        # Check first run
        GLib.idle_add(self.check_first_run)

    def check_first_run(self):
        if not self.config_handler.config_exists():
            self.on_settings_clicked(None)

    def update_ui_status(self):
        status = self.vpn_manager.get_status()
        if status == 'connected':
            self.status_page.set_title("Connected")
            self.status_page.set_icon_name("network-vpn-symbolic")
            self.connect_switch.set_active(True)
        elif status == 'disconnected':
            self.status_page.set_title("Disconnected")
            self.status_page.set_icon_name("network-vpn-disabled-symbolic")
            self.connect_switch.set_active(False)
        elif status == 'not_found':
            self.status_page.set_title("Container Missing")
            self.status_page.set_icon_name("dialog-warning-symbolic")
        return True

    def on_switch_state_set(self, switch, state):
        if state:
            threading.Thread(target=self.vpn_manager.connect, daemon=True).start()
        else:
            threading.Thread(target=self.vpn_manager.disconnect, daemon=True).start()
        return False

    def on_settings_clicked(self, btn):
        settings = SettingsWindow(self, self.config_handler, self.vpn_manager)
        settings.present()

    def on_destroy(self, *args):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)

class KerioApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id='com.cognitera.kerio-rpm',
                         flags=Gio.ApplicationFlags.FLAGS_NONE, **kwargs)
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = KerioWindow(application=self)
        self.win.present()

    def do_startup(self):
        # Correctly chain up to Gio.Application.do_startup
        Gio.Application.do_startup(self)
        # Tray logic could go here in a separate process if needed
        # but for now let's fix the crash

