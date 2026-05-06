import unittest
from config_handler import xor_cipher, xor_decode

class TestConfig(unittest.TestCase):
    def test_xor_cipher(self):
        """Test encryption logic and prefix."""
        original = "password123"
        encoded = xor_cipher(original)
        self.assertTrue(encoded.startswith("XOR:"))
        # 'p' (0x70) ^ 0x39 = 0x49
        # 'a' (0x61) ^ 0x0c = 0x6d
        self.assertEqual(encoded[4:8], "496d")

    def test_xor_decode(self):
        """Test decoding logic."""
        encoded = "XOR:496d"
        decoded = xor_decode(encoded)
        self.assertEqual(decoded, "pa")

    def test_round_trip(self):
        """Test that encoding then decoding returns original text."""
        original = "Hello World! 123"
        encoded = xor_cipher(original)
        decoded = xor_decode(encoded)
        self.assertEqual(decoded, original)

    def test_empty_string(self):
        """Test edge case: empty strings."""
        self.assertEqual(xor_cipher(""), "XOR:")
        self.assertEqual(xor_decode("XOR:"), "")

    def test_no_prefix(self):
        """Test that strings without XOR: prefix are returned unchanged."""
        self.assertEqual(xor_decode("plain"), "plain")

    def test_type_errors(self):
        """Test basic type checking."""
        with self.assertRaises(TypeError):
            xor_cipher(123) # type: ignore
        with self.assertRaises(TypeError):
            xor_decode(None) # type: ignore

if __name__ == "__main__":
    unittest.main()
