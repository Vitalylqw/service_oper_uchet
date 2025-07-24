"""
Unit tests for domain value objects.
"""

from decimal import Decimal

import pytest

from src.domain.value_objects import HashKey, Money, Period, Status


@pytest.mark.unit
class TestMoney:
    """Tests for Money value object."""

    def test_money_creation(self):
        """Test Money creation with valid data."""
        money = Money(amount=Decimal("100.50"), currency="RUB")
        assert money.amount == Decimal("100.50")
        assert money.currency == "RUB"

    def test_money_rounding(self):
        """Test Money rounding to 2 decimal places."""
        money = Money(amount=Decimal("100.567"))
        assert money.amount == Decimal("100.57")

    def test_money_addition(self):
        """Test Money addition."""
        money1 = Money(amount=Decimal("100.50"))
        money2 = Money(amount=Decimal("50.25"))
        result = money1 + money2
        assert result.amount == Decimal("150.75")
        assert result.currency == "RUB"

    def test_money_subtraction(self):
        """Test Money subtraction."""
        money1 = Money(amount=Decimal("100.50"))
        money2 = Money(amount=Decimal("50.25"))
        result = money1 - money2
        assert result.amount == Decimal("50.25")

    def test_money_multiplication(self):
        """Test Money multiplication."""
        money = Money(amount=Decimal("100.00"))
        result = money * 1.5
        assert result.amount == Decimal("150.00")

    def test_money_different_currencies_error(self):
        """Test error when adding different currencies."""
        money1 = Money(amount=Decimal("100"), currency="RUB")
        money2 = Money(amount=Decimal("100"), currency="USD")

        with pytest.raises(ValueError, match="Cannot add different currencies"):
            money1 + money2

    def test_money_negative_amount_error(self):
        """Test error with negative amount."""
        with pytest.raises(ValueError, match="Amount cannot be negative"):
            Money(amount=Decimal("-100"))

    def test_money_invalid_currency_error(self):
        """Test error with invalid currency."""
        with pytest.raises(ValueError, match="Currency code must be 3 characters"):
            Money(amount=Decimal("100"), currency="R")

    def test_money_string_representation(self):
        """Test Money string representation."""
        money = Money(amount=Decimal("100.50"), currency="RUB")
        assert str(money) == "100.50 RUB"

    def test_money_equality(self):
        """Test Money equality."""
        money1 = Money(amount=Decimal("100.50"))
        money2 = Money(amount=Decimal("100.50"))
        money3 = Money(amount=Decimal("100.51"))

        assert money1 == money2
        assert money1 != money3


@pytest.mark.unit
class TestPeriod:
    """Tests for Period value object."""

    def test_period_creation(self):
        """Test Period creation with valid data."""
        period = Period(month="Май", year="2025", full_name="Май 2025")
        assert period.month == "Май"
        assert period.year == "2025"
        assert period.full_name == "Май 2025"

    def test_period_from_sheet_name(self):
        """Test Period creation from sheet name."""
        period = Period.from_sheet_name("Май 2025")
        assert period.month == "Май"
        assert period.year == "2025"
        assert period.full_name == "Май 2025"

    def test_period_from_sheet_name_lowercase(self):
        """Test Period creation from lowercase sheet name."""
        period = Period.from_sheet_name("май 2025")
        assert period.month == "Май"
        assert period.year == "2025"

    def test_period_invalid_month_error(self):
        """Test error with invalid month."""
        with pytest.raises(ValueError, match="Invalid month name"):
            Period(month="Invalid", year="2025", full_name="Invalid 2025")

    def test_period_invalid_year_error(self):
        """Test error with invalid year."""
        with pytest.raises(ValueError, match="Year must be 4 digits"):
            Period(month="Май", year="25", full_name="Май 25")

    def test_period_year_out_of_range_error(self):
        """Test error with year out of range."""
        with pytest.raises(ValueError, match="Year must be between 2020 and 2030"):
            Period(month="Май", year="2050", full_name="Май 2050")

    def test_period_string_representation(self):
        """Test Period string representation."""
        period = Period(month="Май", year="2025", full_name="Май 2025")
        assert str(period) == "Май 2025"


@pytest.mark.unit
class TestHashKey:
    """Tests for HashKey value object."""

    def test_hashkey_creation(self):
        """Test HashKey creation."""
        hash_key = HashKey(value="abc123def456", algorithm="md5")
        assert hash_key.value == "abc123def456"
        assert hash_key.algorithm == "md5"

    def test_hashkey_from_dict(self):
        """Test HashKey creation from dictionary."""
        data = {"name": "test", "value": 123}
        hash_key = HashKey.from_dict(data)
        assert len(hash_key.value) == 32  # MD5 hash length
        assert hash_key.algorithm == "md5"

    def test_hashkey_from_string(self):
        """Test HashKey creation from string."""
        hash_key = HashKey.from_string("test string")
        assert len(hash_key.value) == 32  # MD5 hash length
        assert hash_key.algorithm == "md5"

    def test_hashkey_consistency(self):
        """Test HashKey consistency - same input produces same hash."""
        data = {"name": "test", "value": 123}
        hash1 = HashKey.from_dict(data)
        hash2 = HashKey.from_dict(data)
        assert hash1.value == hash2.value

    def test_hashkey_invalid_value_error(self):
        """Test error with invalid hash value."""
        with pytest.raises(ValueError, match="Hash value must be hexadecimal"):
            HashKey(value="invalid_hash_123!")

    def test_hashkey_empty_value_error(self):
        """Test error with empty hash value."""
        with pytest.raises(ValueError, match="Hash value cannot be empty"):
            HashKey(value="")

    def test_hashkey_equality(self):
        """Test HashKey equality."""
        hash1 = HashKey(value="abc123")
        hash2 = HashKey(value="abc123")
        hash3 = HashKey(value="def456")

        assert hash1 == hash2
        assert hash1 != hash3

    def test_hashkey_string_representation(self):
        """Test HashKey string representation."""
        hash_key = HashKey(value="abc123")
        assert str(hash_key) == "abc123"


@pytest.mark.unit
class TestStatus:
    """Tests for Status enum."""

    def test_status_values(self):
        """Test Status enum values."""
        assert Status.PENDING == "pending"
        assert Status.COMPLETED == "completed"
        assert Status.SHIPPED == "shipped"
        assert Status.PAID == "paid"

    def test_status_from_string_russian(self):
        """Test Status creation from Russian strings."""
        assert Status.from_string("да") == Status.COMPLETED
        assert Status.from_string("нет") == Status.PENDING
        assert Status.from_string("отгружен") == Status.SHIPPED
        assert Status.from_string("оплачен") == Status.PAID

    def test_status_from_string_english(self):
        """Test Status creation from English strings."""
        assert Status.from_string("shipped") == Status.SHIPPED
        assert Status.from_string("paid") == Status.PAID
        assert Status.from_string("completed") == Status.COMPLETED

    def test_status_from_string_case_insensitive(self):
        """Test Status creation is case insensitive."""
        assert Status.from_string("ДА") == Status.COMPLETED
        assert Status.from_string("SHIPPED") == Status.SHIPPED

    def test_status_from_string_none(self):
        """Test Status creation from None/empty."""
        assert Status.from_string(None) is None
        assert Status.from_string("") is None

    def test_status_from_string_unknown_default(self):
        """Test Status creation from unknown string defaults to PENDING."""
        assert Status.from_string("unknown") == Status.PENDING
