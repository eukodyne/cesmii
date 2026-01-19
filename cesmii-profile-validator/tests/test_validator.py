"""Tests for CESMII SM Profile Validator."""

import pytest
from pathlib import Path

from cesmii_validator import ProfileValidator, ValidationResult, load_profile, validate_payload


# Path to test profiles
PROFILES_DIR = Path(__file__).parent.parent.parent / "smprofiles"


@pytest.fixture
def workorder_profile():
    return load_profile(PROFILES_DIR / "WorkOrderV1.jsonld")


@pytest.fixture
def feedingredient_profile():
    return load_profile(PROFILES_DIR / "FeedIngredientV1.jsonld")


@pytest.fixture
def referenced_profiles(feedingredient_profile):
    return {
        "https://www.github.com/eukodyne/cesmii/smprofiles/FeedIngredientV1": feedingredient_profile,
    }


@pytest.fixture
def valid_payload():
    return {
        "$namespace": "https://www.github.com/eukodyne/cesmii/smprofiles/WorkOrderV1",
        "WorkOrderID": "e68308bc-4f85-46f8-8778-73efe5119096",
        "WorkOrderNumber": 100026,
        "TimeZone": {"offset": -360, "daylightSavingInOffset": False},
        "StartTimeLocal": "2026-01-16T08:02:37.789055-06:00",
        "StartTimeUTC": "2026-01-16T14:02:37.789055Z",
        "EndTimeLocal": "2026-01-16T16:02:37.789055-06:00",
        "EndTimeUTC": "2026-01-16T22:02:37.789055Z",
        "ProductID": "9c6fc633-9dbb-40f4-a63a-f6e07b2da557",
        "ProductNumber": 2221,
        "ProductName": "Product A",
        "LotNumber": "LOT-20260116-080237",
        "UnitOfMeasure": "CS",
        "Quantity": 108.0,
        "WeightUnitOfMeasure": "lb",
        "Weight": 216.0,
        "FeedIngredients": [
            {
                "$namespace": "https://www.github.com/eukodyne/cesmii/smprofiles/FeedIngredientV1",
                "ProductID": "4d81e339-d83b-4c37-b4c0-77d32033b9ec",
                "ProductNumber": 2001,
                "ProductName": "Product A1",
                "LotNumber": "42GS6E",
                "UnitOfMeasure": "CS",
                "Quantity": 10.8,
                "WeightUnitOfMeasure": "lb",
                "Weight": 21.6,
            }
        ],
    }


class TestOPCTypeValidation:
    """Test OPC UA data type validation."""

    def test_valid_int32(self, workorder_profile):
        payload = {"WorkOrderNumber": 100}
        result = validate_payload(payload, workorder_profile)
        # Should not have error for WorkOrderNumber
        errors_for_field = [e for e in result.errors if "WorkOrderNumber" in e.path]
        assert len(errors_for_field) == 0

    def test_invalid_int32_string(self, workorder_profile):
        payload = {"WorkOrderNumber": "not-a-number"}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "WorkOrderNumber" in e.path]
        assert len(errors_for_field) == 1
        assert "Invalid type" in errors_for_field[0].message

    def test_valid_double(self, workorder_profile):
        payload = {"Quantity": 108.5}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "Quantity" in e.path]
        assert len(errors_for_field) == 0

    def test_valid_double_as_int(self, workorder_profile):
        """Integers should be valid for Double fields."""
        payload = {"Quantity": 100}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "Quantity" in e.path]
        assert len(errors_for_field) == 0

    def test_invalid_double(self, workorder_profile):
        payload = {"Quantity": "one hundred"}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "Quantity" in e.path]
        assert len(errors_for_field) == 1

    def test_valid_utc_time(self, workorder_profile):
        payload = {"StartTimeUTC": "2026-01-16T14:02:37.789055Z"}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "StartTimeUTC" in e.path]
        assert len(errors_for_field) == 0

    def test_invalid_utc_time_no_z(self, workorder_profile):
        """UTC time must end with Z."""
        payload = {"StartTimeUTC": "2026-01-16T14:02:37.789055"}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "StartTimeUTC" in e.path]
        assert len(errors_for_field) == 1


class TestTimeZoneValidation:
    """Test TimeZoneDataType validation."""

    def test_valid_timezone(self, workorder_profile):
        payload = {"TimeZone": {"offset": -360, "daylightSavingInOffset": False}}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "TimeZone" in e.path]
        assert len(errors_for_field) == 0

    def test_timezone_missing_offset(self, workorder_profile):
        payload = {"TimeZone": {"daylightSavingInOffset": False}}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "TimeZone.offset" in e.path]
        assert len(errors_for_field) == 1
        assert "Missing required field" in errors_for_field[0].message

    def test_timezone_missing_dst(self, workorder_profile):
        payload = {"TimeZone": {"offset": -360}}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "daylightSavingInOffset" in e.path]
        assert len(errors_for_field) == 1

    def test_timezone_offset_out_of_range(self, workorder_profile):
        payload = {"TimeZone": {"offset": 99999, "daylightSavingInOffset": False}}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "TimeZone.offset" in e.path]
        assert len(errors_for_field) == 1

    def test_timezone_wrong_type(self, workorder_profile):
        payload = {"TimeZone": "America/Chicago"}
        result = validate_payload(payload, workorder_profile)
        errors_for_field = [e for e in result.errors if "TimeZone" in e.path]
        assert len(errors_for_field) == 1


class TestNestedProfileValidation:
    """Test nested profile (FeedIngredients) validation."""

    def test_valid_feed_ingredients(self, workorder_profile, referenced_profiles):
        payload = {
            "FeedIngredients": [
                {
                    "ProductID": "test-id",
                    "ProductNumber": 1001,
                    "ProductName": "Test Ingredient",
                    "Quantity": 10.5,
                }
            ]
        }
        result = validate_payload(payload, workorder_profile, referenced_profiles)
        errors_for_field = [e for e in result.errors if "FeedIngredients" in e.path]
        assert len(errors_for_field) == 0

    def test_feed_ingredients_not_array(self, workorder_profile, referenced_profiles):
        payload = {"FeedIngredients": "not-an-array"}
        result = validate_payload(payload, workorder_profile, referenced_profiles)
        errors_for_field = [e for e in result.errors if "FeedIngredients" in e.path]
        assert len(errors_for_field) == 1
        assert "Expected array" in errors_for_field[0].message

    def test_feed_ingredient_invalid_type(self, workorder_profile, referenced_profiles):
        payload = {
            "FeedIngredients": [
                {
                    "ProductID": "test-id",
                    "ProductNumber": "not-a-number",  # Should be Int64
                    "Quantity": 10.5,
                }
            ]
        }
        result = validate_payload(payload, workorder_profile, referenced_profiles)
        errors_for_field = [e for e in result.errors if "ProductNumber" in e.path]
        assert len(errors_for_field) == 1

    def test_multiple_feed_ingredients(self, workorder_profile, referenced_profiles):
        payload = {
            "FeedIngredients": [
                {"ProductID": "id1", "ProductNumber": 1001, "Quantity": 10.0},
                {"ProductID": "id2", "ProductNumber": 1002, "Quantity": 20.0},
                {"ProductID": "id3", "ProductNumber": 1003, "Quantity": 30.0},
            ]
        }
        result = validate_payload(payload, workorder_profile, referenced_profiles)
        errors_for_field = [e for e in result.errors if "FeedIngredients" in e.path]
        assert len(errors_for_field) == 0


class TestFullPayloadValidation:
    """Test full payload validation."""

    def test_valid_full_payload(self, workorder_profile, referenced_profiles, valid_payload):
        result = validate_payload(valid_payload, workorder_profile, referenced_profiles)
        assert result.valid
        assert len(result.errors) == 0

    def test_validation_result_str(self, workorder_profile):
        payload = {"WorkOrderNumber": "invalid"}
        result = validate_payload(payload, workorder_profile)
        result_str = str(result)
        assert "Invalid" in result_str
        assert "error" in result_str


class TestLoadProfile:
    """Test profile loading."""

    def test_load_from_file(self):
        profile = load_profile(PROFILES_DIR / "WorkOrderV1.jsonld")
        assert profile is not None
        assert "@context" in profile
        assert "cesmii:attributes" in profile

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_profile("/nonexistent/path/profile.jsonld")
