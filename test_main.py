import unittest
from main import GF256, GF256Poly, RSCodec

class TestReedSolomonDecode(unittest.TestCase):
    def setUp(self):
        self.codec = RSCodec(255,251)
        self.msg = "This is a test message"
        self.codeword = self.codec.encode(self.msg)

    def test_zero_syndromes_for_uncorrupted_message(self):
        synds = self.codec.decode(self.codeword.coeffs)

        self.assertEqual(
            synds,
            [0] * self.codec.nsym,
            f"Expected all zeros, got {synds}",
        )

    def test_more_syndromes_for_corrupted_message(self):

        encoded_msg = bytes(self.codeword.coeffs)

        corrupted_msg = bytearray(encoded_msg)
        corrupted_msg[0] ^= 0xFF

        synds = self.codec.decode(corrupted_msg)
        n = sum(synds)

        self.assertTrue(
            any(s != 0 for s in synds),
            "Syndromes should be non-zero when errors are present",
        )

    def test_decode_matches_direct_horner_eval(self):
        encoded_msg = bytes(self.codeword.coeffs)

        corrupted_msg = bytearray(encoded_msg)
        corrupted_msg[5] ^= 0x42
        corrupted_msg[12] ^= 0xAB

        synds_decode = self.codec.decode(corrupted_msg)

        R_x = GF256Poly(list(corrupted_msg))

        synds_eval = [
            R_x.eval(GF256.pow(2,i)) for i in range(self.codec.nsym)
        ]

        self.assertEqual(
            synds_decode,
            synds_eval,
            f"decode() syndromes {synds_decode} do not match Horner eval {synds_eval}",
         )

class TestBerlekampMassey(unittest.TestCase):
    def setUp(self):
        self.codec = RSCodec(255, 251)
        self.msg = "This is a test message"
        self.codeword = self.codec.encode(self.msg)

    def test_no_errors_returns_constant_one(self):
        synds = self.codec.decode(self.codeword.coeffs)
        error_poly = self.codec.berlekamp_massey(synds)

        self.assertEqual(
            error_poly.coeffs,
            [1],
            f"Expected Lambda(x) = [1], got {error_poly.coeffs}",
         )

    def test_single_error_locator_root(self):
        corrupted = bytearray(self.codeword.coeffs)
        corrupted[5] ^= 0xA5

        synds = self.codec.decode(corrupted)
        error_poly = self.codec.berlekamp_massey(synds)

        self.assertEqual(
            len(error_poly.coeffs),
            2,
            f"Expected degree-1 polynomial, got {error_poly.coeffs}",
        )

if __name__ == "__main__":
    unittest.main()
