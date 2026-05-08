import os
import pathlib
import xml.etree.ElementTree as ET

def xor_cipher(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    # Official Kerio XOR key is 0x55
    key = 0x55
    result = ""
    for char in text:
        xor_val = ord(char) ^ key
        result += f"{xor_val:02x}"
    return "XOR:" + result

def xor_decode(encoded_text: str) -> str:
    if not isinstance(encoded_text, str):
        raise TypeError("Input must be a string")
    if not encoded_text.startswith("XOR:"):
        return encoded_text
    hex_data = encoded_text[4:]
    key = 0x55
    result = ""
    for i in range(0, len(hex_data), 2):
        hex_pair = hex_data[i:i+2]
        if len(hex_pair) < 2: break
        xor_val = int(hex_pair, 16)
        char_code = xor_val ^ key
        result += chr(char_code)
    return result

class ConfigHandler:
    def __init__(self, config_path=None):
        if config_path is None:
            self.config_path = os.path.expanduser("~/.config/kerio-rpm/kerio-kvc.conf")
        else:
            self.config_path = config_path
            
    def config_exists(self):
        return os.path.exists(self.config_path)

    def load_config(self):
        config = {
            "server": "", 
            "port": "4090", 
            "username": "", 
            "password": "", 
            "fingerprint": "",
            "custom_routes": ""
        }
        if not self.config_exists():
            return config
            
        try:
            tree = ET.parse(self.config_path)
            root = tree.getroot()
            conn = root.find(".//connection")
            if conn is not None:
                config["server"] = conn.findtext("server", "")
                config["port"] = conn.findtext("port", "4090")
                config["username"] = conn.findtext("username", "")
                config["password"] = xor_decode(conn.findtext("password", ""))
                config["fingerprint"] = conn.findtext("fingerprint", "")
                
            # Load custom routes from our custom section
            app_settings = root.find(".//app_settings")
            if app_settings is not None:
                config["custom_routes"] = app_settings.findtext("custom_routes", "")
        except Exception:
            pass
        return config
        
    def save_config(self, server, username, password, fingerprint, custom_routes="", port="4090"):
        pathlib.Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        
        root = ET.Element("config")
        connections = ET.SubElement(root, "connections")
        conn = ET.SubElement(connections, "connection", type="persistent")
        ET.SubElement(conn, "server").text = server
        ET.SubElement(conn, "port").text = port
        ET.SubElement(conn, "username").text = username
        ET.SubElement(conn, "password").text = xor_cipher(password)
        ET.SubElement(conn, "fingerprint").text = fingerprint
        ET.SubElement(conn, "active").text = "1"
        
        # Add our custom settings section for routes
        app_settings = ET.SubElement(root, "app_settings")
        ET.SubElement(app_settings, "custom_routes").text = custom_routes
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(self.config_path, encoding="UTF-8", xml_declaration=True)
        
        try:
            os.chmod(self.config_path, 0o644)
        except: pass
