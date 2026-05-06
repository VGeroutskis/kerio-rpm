def xor_cipher(text):
    """
    Kerio XOR logic implementation.
    XORs each character with a cycling key and formats the result as hex.
    """
    key = [0x39, 0x0c, 0x0f, 0x26, 0x67, 0x13, 0x02, 0x6d, 0x78, 0x2c]
    result = ""
    for i, char in enumerate(text):
        # XOR each char with key (cycling)
        xor_val = ord(char) ^ key[i % len(key)]
        # Format as 2-digit hex
        result += f"{xor_val:02x}"
    return "XOR:" + result
