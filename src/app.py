import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio
from vpn_manager import VPNManager

class KerioWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Kerio VPN")
        self.set_default_size(400, 300)

        self.vpn_manager = VPNManager()

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

        # Update status periodically
        GLib.timeout_add_seconds(2, self.update_status)
        self.update_status()

    def update_status(self):
        status = self.vpn_manager.get_status()
        if status == "connected":
            self.status_page.set_title("Connected")
            self.status_page.set_description("VPN is active")
            self.switch.set_state(True)
        elif status == "disconnected":
            self.status_page.set_title("Disconnected")
            self.status_page.set_description("VPN is inactive")
            self.switch.set_state(False)
        elif status == "not_found":
            self.status_page.set_title("Container Not Found")
            self.status_page.set_description("Container 'keriovpn-native' does not exist")
            self.switch.set_state(False)
        elif status == "transitioning":
            self.status_page.set_title("Transitioning...")
            self.status_page.set_description("Container is changing state")
        else:
            self.status_page.set_title("Error")
            self.status_page.set_description(f"Status: {status}")
            self.switch.set_state(False)
        return True

    def on_switch_state_set(self, switch, state):
        if state:
            self.vpn_manager.connect()
        else:
            self.vpn_manager.disconnect()
        # The update_status will sync the UI
        return True

class KerioApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.kerio_rpm",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = KerioWindow(application=self)
        win.present()
