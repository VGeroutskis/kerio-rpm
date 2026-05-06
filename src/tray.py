import sys
import gi

def tray_main(status_queue, cmd_queue):
    try:
        gi.require_version('Gtk', '3.0')
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import Gtk as Gtk3
        from gi.repository import AppIndicator3
        from gi.repository import GLib as GLib3
    except Exception as e:
        sys.stderr.write(f"Tray initialization failed: {e}\n")
        return

    indicator = AppIndicator3.Indicator.new(
        "kerio-vpn",
        "network-vpn-no-route-symbolic",
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    menu = Gtk3.Menu()
    
    item_show = Gtk3.MenuItem(label="Show")
    item_show.connect("activate", lambda _: cmd_queue.put("show"))
    menu.append(item_show)
    
    item_hide = Gtk3.MenuItem(label="Hide")
    item_hide.connect("activate", lambda _: cmd_queue.put("hide"))
    menu.append(item_hide)
    
    menu.append(Gtk3.SeparatorMenuItem())
    
    item_connect = Gtk3.MenuItem(label="Connect")
    item_connect.connect("activate", lambda _: cmd_queue.put("connect"))
    menu.append(item_connect)
    
    item_disconnect = Gtk3.MenuItem(label="Disconnect")
    item_disconnect.connect("activate", lambda _: cmd_queue.put("disconnect"))
    menu.append(item_disconnect)
    
    menu.append(Gtk3.SeparatorMenuItem())
    
    item_quit = Gtk3.MenuItem(label="Quit")
    item_quit.connect("activate", lambda _: cmd_queue.put("quit"))
    menu.append(item_quit)
    
    menu.show_all()
    indicator.set_menu(menu)

    def poll_status():
        try:
            while not status_queue.empty():
                status = status_queue.get_nowait()
                if status == "connected":
                    indicator.set_icon_full("network-vpn-symbolic", "Connected")
                    item_connect.set_label("Connected")
                    item_connect.set_sensitive(False)
                    item_disconnect.set_label("Disconnect")
                    item_disconnect.set_sensitive(True)
                elif status == "transitioning":
                    indicator.set_icon_full("network-vpn-acquiring-symbolic", "Transitioning")
                    item_connect.set_label("Connecting...")
                    item_connect.set_sensitive(False)
                    item_disconnect.set_label("Disconnecting...")
                    item_disconnect.set_sensitive(False)
                else: # disconnected, not_found, etc.
                    indicator.set_icon_full("network-vpn-no-route-symbolic", "Disconnected")
                    item_connect.set_label("Connect")
                    item_connect.set_sensitive(True)
                    item_disconnect.set_label("Disconnected")
                    item_disconnect.set_sensitive(False)
        except Exception:
            pass
        return True

    GLib3.timeout_add(500, poll_status)
    Gtk3.main()
