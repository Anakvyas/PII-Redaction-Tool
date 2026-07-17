from utils.validators import is_valid_ipv4, luhn_is_valid


class TestLuhnIsValid:
    def test_valid_visa_test_number(self):
        assert luhn_is_valid("4539148803436467") is True

    def test_invalid_checksum_rejected(self):
        assert luhn_is_valid("4539148803436468") is False

    def test_strips_spaces_and_dashes_before_checking(self):
        assert luhn_is_valid("4539 1488 0343 6467") is True
        assert luhn_is_valid("4539-1488-0343-6467") is True

    def test_rejects_fewer_than_twelve_digits(self):
        # 11 digits — rejected purely on length, regardless of checksum.
        assert luhn_is_valid("12345678901") is False
        assert luhn_is_valid("1234567890") is False

    def test_rejects_empty_string(self):
        assert luhn_is_valid("") is False

    def test_rejects_non_digit_garbage(self):
        assert luhn_is_valid("abcd-efgh-ijkl-mnop") is False


class TestIsValidIpv4:
    def test_accepts_standard_address(self):
        assert is_valid_ipv4("192.168.1.15") is True

    def test_accepts_all_zeros_and_broadcast(self):
        assert is_valid_ipv4("0.0.0.0") is True
        assert is_valid_ipv4("255.255.255.255") is True

    def test_rejects_octet_over_255(self):
        assert is_valid_ipv4("256.1.1.1") is False
        assert is_valid_ipv4("192.168.1.999") is False

    def test_rejects_wrong_number_of_octets(self):
        assert is_valid_ipv4("192.168.1") is False
        assert is_valid_ipv4("192.168.1.1.1") is False

    def test_rejects_non_numeric_octet(self):
        assert is_valid_ipv4("192.168.one.1") is False

    def test_rejects_leading_zero_octet(self):
        """A leading zero (e.g. "192.168.001.1") is rejected rather than
        silently reinterpreted — avoids the classic octal-parsing ambiguity."""
        assert is_valid_ipv4("192.168.001.1") is False
        assert is_valid_ipv4("192.168.01.1") is False

    def test_bare_zero_octet_is_still_valid(self):
        assert is_valid_ipv4("10.0.0.1") is True
