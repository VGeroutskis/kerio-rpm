import unittest
import sys
import os

# Add src to path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.config_handler import xor_cipher
except ImportError:
    # This is expected to fail initially as the file doesn't exist
    xor_cipher = None

class TestConfig(unittest.TestCase):
    def test_xor_cipher(self):
        if xor_cipher is None:
            self.fail("xor_cipher not imported. src/config_handler.py might be missing or empty.")
            
        original = "password123"
        encoded = xor_cipher(original)
        self.assertTrue(encoded.startswith("XOR:"), f"Encoded string '{encoded}' does not start with 'XOR:'")
        
        # Kerio logic test: XOR with [0x39, 0x0c, 0x0f, 0x26, 0x67, 0x13, 0x02, 0x6d, 0x78, 0x2c]
        # 'p' (0x70) ^ 0x39 = 0x49
        # 'a' (0x61) ^ 0x0c = 0x6d
        self.assertEqual(encoded[4:8], "496d", f"Encoded string '{encoded}' has incorrect XOR values")

if __name__ == "__main__":
    unittest.main()
