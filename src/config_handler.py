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
