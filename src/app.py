import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
import threading
import subprocess
import os
import shutil
from config_handler import ConfigHandler
from vpn_manager import VPNManager

class SettingsWindow(Adw.Window):
    def __init__(self, parent, config_handler, vpn_manager):
        super().__init__(transient_for=parent, modal=True)
        self.config_handler = config_handler
        self.vpn_manager = vpn_manager
        self.set_title("Kerio VPN Settings")
        self.set_default_size(400, 450)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(24); box.set_margin_end(24); box.set_margin_top(24); box.set_margin_bottom(24)
        self.set_content(box)

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

        # Import Button
        import_btn = Gtk.Button(label="Import from .conf file")
        import_btn.connect("clicked", self.on_import_clicked)
        box.append(import_btn)

        save_btn = Gtk.Button(label="Save and Setup Container", css_classes=["suggested-action"])
        save_btn.connect("clicked", self.on_save_clicked)
        box.append(save_btn)

        config = self.config_handler.load_config()
        if config:
            self.server_entry.set_text(config.get('server', ''))
            self.user_entry.set_text(config.get('username', ''))
            self.fp_entry.set_text(config.get('fingerprint', ''))

    def on_import_clicked(self, btn):
        dialog = Gtk.FileChooser                    # Simplified for this turn, using proper one
        # Logic to open file chooser
        native = Gtk.FileChooserNative.new(
            title="Open Kerio Config",
            parent=self.get_root(),
            action=Gtk.FileChooserAction.OPEN,
            accept_label="_Open",
            cancel_label="_Cancel",
        )
        native.connect("response", self.on_import_file_response)
        native.show()

    def on_import_file_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file_path = dialog.get_file().get_path()
            # Basic parsing of manual XML
            import xml.etree.ElementTree as ET
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                conn = root.find(".//connection")
                if conn is not None:
                    self.server_entry.set_text(conn.findtext("server", ""))
                    self.user_entry.set_text(conn.findtext("username", ""))
                    self.fp_entry.set_text(conn.findtext("fingerprint", ""))
            except: pass
        dialog.destroy()

    def on_fetch_clicked(self, btn):
        server = self.server_entry.get_text()
        if server:
            def _fetch():
                try:
                    cmd = f"openssl s_client -connect {server}:4090 < /dev/null 2>/dev/null | openssl x509 -fingerprint -md5 -noout | sed 's/.*=//'"
                    fp = subprocess.check_output(cmd, shell=True, text=True).strip()
                    GLib.idle_add(self.fp_entry.set_text, fp)
                except: pass
            threading.Thread(target=_fetch, daemon=True).start()

    def on_save_clicked(self, btn):
        self.config_handler.save_config(
            server=self.server_entry.get_text(),
            username=self.user_entry.get_text(),
            password=self.pass_entry.get_text(),
            fingerprint=self.fp_entry.get_text()
        )
        # Force container setup
        threading.Thread(target=self.vpn_manager.ensure_container_exists, daemon=True).start()
        self.close()

class KerioWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Kerio VPN")
        self.set_default_size(450, 450)
        self.vpn_manager = VPNManager()
        self.config_handler = ConfigHandler()

        self.status_page = Adw.StatusPage(title="Checking status...", icon_name="network-vpn-acquiring-symbolic")
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_margin_start(20); main_box.set_margin_end(20); main_box.set_margin_top(20); main_box.set_margin_bottom(20)
        main_box.append(self.status_page)

        self.connect_switch = Gtk.Switch(halign=Gtk.Align.CENTER)
        self.connect_switch.connect("state-set", self.on_switch_state_set)
        main_box.append(self.connect_switch)

        btn_box = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER)
        settings_btn = Gtk.Button(label="Settings")
        settings_btn.connect("clicked", self.on_settings_clicked)
        btn_box.append(settings_btn)

        quit_btn = Gtk.Button(label="Quit")
        quit_btn.connect("clicked", lambda x: self.get_application().quit())
        btn_box.append(quit_btn)
        
        main_box.append(btn_box)

        self.set_content(main_box)
        self.timeout_id = GLib.timeout_add_seconds(2, self.update_ui_status)
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
            self.status_page.set_description("Go to Settings and Save to initialize")
            self.status_page.set_icon_name("dialog-warning-symbolic")
        return True

    def on_switch_state_set(self, switch, state):
        target = self.vpn_manager.connect if state else self.vpn_manager.disconnect
        threading.Thread(target=target, daemon=True).start()
        return False

    def on_settings_clicked(self, btn):
        SettingsWindow(self, self.config_handler, self.vpn_manager).present()

class KerioApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id='com.cognitera.kerio-rpm', **kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = KerioWindow(application=app)
        win.present()
