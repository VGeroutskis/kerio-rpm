import os
import pathlib

def xor_cipher(text: str) -> str:
    """
    Kerio XOR logic implementation.
    XORs each character with a cycling key and formats the result as hex.
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
        
    key = [0x39, 0x0c, 0x0f, 0x26, 0x67, 0x13, 0x02, 0x6d, 0x78, 0x2c]
    result = ""
    for i, char in enumerate(text):
        # XOR each char with key (cycling)
        xor_val = ord(char) ^ key[i % len(key)]
        # Format as 2-digit hex
        result += f"{xor_val:02x}"
    return "XOR:" + result

def xor_decode(encoded_text: str) -> str:
    """
    Decodes Kerio XOR format.
    Removes 'XOR:' prefix, then XORs each hex pair with cycling key.
    """
    if not isinstance(encoded_text, str):
        raise TypeError("Input must be a string")
        
    if not encoded_text.startswith("XOR:"):
        return encoded_text
        
    hex_data = encoded_text[4:]
    key = [0x39, 0x0c, 0x0f, 0x26, 0x67, 0x13, 0x02, 0x6d, 0x78, 0x2c]
    result = ""
    
    for i in range(0, len(hex_data), 2):
        hex_pair = hex_data[i:i+2]
        if len(hex_pair) < 2:
            break
        xor_val = int(hex_pair, 16)
        # XOR back with key
        char_code = xor_val ^ key[(i // 2) % len(key)]
        result += chr(char_code)
        
    return result

class ConfigHandler:
    def __init__(self, config_path=None):
        if config_path is None:
            self.config_path = os.path.expanduser("~/.config/kerio-rpm/kerio-kvc.conf")
        else:
            self.config_path = config_path
            
    def load(self):
        config = {"server": "", "port": "4090", "username": "", "password": ""}
        if not os.path.exists(self.config_path):
            return config
            
        try:
            with open(self.config_path, "r") as f:
                for line in f:
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip().lower()
                        val = val.strip()
                        if key == "server": config["server"] = val
                        elif key == "port": config["port"] = val
                        elif key == "username": config["username"] = val
                        elif key == "password": config["password"] = xor_decode(val)
        except Exception:
            pass
        return config
        
    def save(self, server, port, username, password):
        # Create directory if it doesn't exist
        pathlib.Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, "w") as f:
            f.write(f"Server = {server}\n")
            f.write(f"Port = {port}\n")
            f.write(f"Username = {username}\n")
            f.write(f"Password = {xor_cipher(password)}\n")
