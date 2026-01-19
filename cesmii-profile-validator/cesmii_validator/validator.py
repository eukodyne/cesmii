"""
CESMII SM Profile Validator

Validates JSON payloads against CESMII Smart Manufacturing Profile definitions.
Supports OPC UA data types and nested profile references.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen


@dataclass
class ValidationError:
    """Represents a single validation error."""

    path: str
    message: str
    expected: str | None = None
    actual: str | None = None

    def __str__(self) -> str:
        msg = f"{self.path}: {self.message}"
        if self.expected and self.actual:
            msg += f" (expected: {self.expected}, got: {self.actual})"
        return msg


@dataclass
class ValidationResult:
    """Result of validating a payload against a profile."""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.valid:
            return "Valid"
        return f"Invalid: {len(self.errors)} error(s)\n" + "\n".join(
            f"  - {e}" for e in self.errors
        )


# OPC UA Data Type Validators
# Based on OPC UA Part 6 - Data Types

def _is_valid_boolean(value: Any) -> bool:
    return isinstance(value, bool)


def _is_valid_int16(value: Any) -> bool:
    return isinstance(value, int) and -32768 <= value <= 32767


def _is_valid_int32(value: Any) -> bool:
    return isinstance(value, int) and -2147483648 <= value <= 2147483647


def _is_valid_int64(value: Any) -> bool:
    return isinstance(value, int) and -9223372036854775808 <= value <= 9223372036854775807


def _is_valid_uint16(value: Any) -> bool:
    return isinstance(value, int) and 0 <= value <= 65535


def _is_valid_uint32(value: Any) -> bool:
    return isinstance(value, int) and 0 <= value <= 4294967295


def _is_valid_uint64(value: Any) -> bool:
    return isinstance(value, int) and 0 <= value <= 18446744073709551615


def _is_valid_float(value: Any) -> bool:
    return isinstance(value, (int, float))


def _is_valid_double(value: Any) -> bool:
    return isinstance(value, (int, float))


def _is_valid_string(value: Any) -> bool:
    return isinstance(value, str)


def _is_valid_datetime(value: Any) -> bool:
    """Validate ISO 8601 datetime string."""
    if not isinstance(value, str):
        return False
    # Basic ISO 8601 pattern
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    return bool(re.match(pattern, value))


def _is_valid_utctime(value: Any) -> bool:
    """Validate UTC time string (must end with Z)."""
    if not isinstance(value, str):
        return False
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*Z$"
    return bool(re.match(pattern, value))


def _is_valid_guid(value: Any) -> bool:
    """Validate GUID/UUID string."""
    if not isinstance(value, str):
        return False
    pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    return bool(re.match(pattern, value))


# Map OPC UA type identifiers to validators
OPC_TYPE_VALIDATORS: dict[str, tuple[callable, str]] = {
    # Using both full URI and short forms
    "opc:Boolean": (_is_valid_boolean, "boolean"),
    "opc:Int16": (_is_valid_int16, "integer (-32768 to 32767)"),
    "opc:Int32": (_is_valid_int32, "integer (-2147483648 to 2147483647)"),
    "opc:Int64": (_is_valid_int64, "integer (64-bit)"),
    "opc:UInt16": (_is_valid_uint16, "unsigned integer (0 to 65535)"),
    "opc:UInt32": (_is_valid_uint32, "unsigned integer (0 to 4294967295)"),
    "opc:UInt64": (_is_valid_uint64, "unsigned integer (64-bit)"),
    "opc:Float": (_is_valid_float, "float"),
    "opc:Double": (_is_valid_double, "double"),
    "opc:String": (_is_valid_string, "string"),
    "opc:DateTime": (_is_valid_datetime, "ISO 8601 datetime"),
    "opc:UtcTime": (_is_valid_utctime, "ISO 8601 UTC time (ending with Z)"),
    "opc:Guid": (_is_valid_guid, "GUID/UUID"),
}


def load_profile(source: str | Path) -> dict[str, Any]:
    """
    Load a CESMII SM Profile from a file path or URL.

    Args:
        source: File path or URL to the profile JSON-LD file

    Returns:
        Parsed profile as a dictionary
    """
    source_str = str(source)

    if source_str.startswith(("http://", "https://")):
        with urlopen(source_str) as response:
            return json.loads(response.read().decode("utf-8"))
    else:
        with open(source, "r") as f:
            return json.load(f)


class ProfileValidator:
    """
    Validates payloads against CESMII Smart Manufacturing Profiles.

    Supports:
    - OPC UA data type validation
    - Nested profile references
    - Array validation with unlimited length
    - TimeZoneDataType structure validation
    """

    def __init__(self, profile: dict[str, Any], referenced_profiles: dict[str, dict] | None = None):
        """
        Initialize validator with a profile.

        Args:
            profile: The CESMII SM Profile (parsed JSON-LD)
            referenced_profiles: Dict mapping namespace URIs to profile dicts for nested types
        """
        self.profile = profile
        self.referenced_profiles = referenced_profiles or {}
        self._parse_profile()

    def _parse_profile(self) -> None:
        """Parse profile to extract attribute/field definitions."""
        # Determine if this is a DataType (uses fields) or ObjectType (uses attributes)
        self.is_data_type = self.profile.get("cesmii:isDataType", False)

        if self.is_data_type:
            self.fields = {
                f.get("cesmii:fieldName"): f
                for f in self.profile.get("cesmii:fields", [])
            }
        else:
            self.fields = {
                a.get("cesmii:browseName"): a
                for a in self.profile.get("cesmii:attributes", [])
            }

        # Extract namespace
        self.namespace = self.profile.get("@id", "")

        # Parse context for type information
        self.context = self.profile.get("@context", {})

    def _get_type_from_context(self, field_name: str) -> str | None:
        """Get the OPC UA type for a field from the @context."""
        ctx_entry = self.context.get(field_name)
        if isinstance(ctx_entry, dict):
            return ctx_entry.get("@type")
        return None

    def _validate_opc_type(
        self, value: Any, opc_type: str, path: str
    ) -> list[ValidationError]:
        """Validate a value against an OPC UA data type."""
        errors = []

        if opc_type in OPC_TYPE_VALIDATORS:
            validator, type_desc = OPC_TYPE_VALIDATORS[opc_type]
            if not validator(value):
                errors.append(
                    ValidationError(
                        path=path,
                        message=f"Invalid type",
                        expected=type_desc,
                        actual=type(value).__name__,
                    )
                )
        elif opc_type == "opc:TimeZoneDataType":
            errors.extend(self._validate_timezone(value, path))
        # Unknown types pass through (could be custom types)

        return errors

    def _validate_timezone(self, value: Any, path: str) -> list[ValidationError]:
        """Validate OPC UA TimeZoneDataType structure."""
        errors = []

        if not isinstance(value, dict):
            errors.append(
                ValidationError(
                    path=path,
                    message="TimeZoneDataType must be an object",
                    expected="object with offset and daylightSavingInOffset",
                    actual=type(value).__name__,
                )
            )
            return errors

        # Validate offset (Int16)
        if "offset" not in value:
            errors.append(
                ValidationError(path=f"{path}.offset", message="Missing required field")
            )
        elif not _is_valid_int16(value["offset"]):
            errors.append(
                ValidationError(
                    path=f"{path}.offset",
                    message="Invalid type",
                    expected="integer (-32768 to 32767)",
                    actual=type(value["offset"]).__name__,
                )
            )

        # Validate daylightSavingInOffset (Boolean)
        if "daylightSavingInOffset" not in value:
            errors.append(
                ValidationError(
                    path=f"{path}.daylightSavingInOffset",
                    message="Missing required field",
                )
            )
        elif not _is_valid_boolean(value["daylightSavingInOffset"]):
            errors.append(
                ValidationError(
                    path=f"{path}.daylightSavingInOffset",
                    message="Invalid type",
                    expected="boolean",
                    actual=type(value["daylightSavingInOffset"]).__name__,
                )
            )

        return errors

    def _validate_nested_profile(
        self, value: Any, profile_ref: str, path: str
    ) -> list[ValidationError]:
        """Validate a value against a nested/referenced profile."""
        errors = []

        # Try to find the referenced profile
        ref_profile = None

        # Check if we have it in referenced_profiles
        for ns, profile in self.referenced_profiles.items():
            if ns in profile_ref or profile_ref in ns:
                ref_profile = profile
                break

        if ref_profile is None:
            # Could not find referenced profile - add warning but don't fail
            return [
                ValidationError(
                    path=path,
                    message=f"Could not validate against referenced profile (not loaded): {profile_ref}",
                )
            ]

        # Create validator for nested profile and validate
        nested_validator = ProfileValidator(ref_profile, self.referenced_profiles)
        result = nested_validator.validate(value, path_prefix=path)
        errors.extend(result.errors)

        return errors

    def validate(
        self, payload: dict[str, Any], path_prefix: str = ""
    ) -> ValidationResult:
        """
        Validate a payload against this profile.

        Args:
            payload: The payload to validate
            path_prefix: Prefix for error paths (used for nested validation)

        Returns:
            ValidationResult with valid flag and any errors
        """
        errors = []
        warnings = []

        if not isinstance(payload, dict):
            errors.append(
                ValidationError(
                    path=path_prefix or "$",
                    message="Payload must be an object",
                    expected="object",
                    actual=type(payload).__name__,
                )
            )
            return ValidationResult(valid=False, errors=errors)

        # Check $namespace matches (if present)
        payload_ns = payload.get("$namespace", "")
        if payload_ns and self.namespace and payload_ns != self.namespace:
            warnings.append(
                f"Payload namespace '{payload_ns}' doesn't match profile namespace '{self.namespace}'"
            )

        # Validate each defined field/attribute
        for field_name, field_def in self.fields.items():
            path = f"{path_prefix}.{field_name}" if path_prefix else field_name

            # Check if field exists in payload
            if field_name not in payload:
                # For now, treat all fields as optional (could add required field support)
                continue

            value = payload[field_name]

            # Get data type from field definition
            data_type_def = field_def.get("cesmii:dataType", {})
            opc_type = data_type_def.get("@id") if isinstance(data_type_def, dict) else None

            # Also check context for type
            if not opc_type:
                opc_type = self._get_type_from_context(field_name)

            # Check if this is an array field
            is_array = field_def.get("cesmii:isArray", False)
            profile_ref = (
                data_type_def.get("cesmii:profileReference")
                if isinstance(data_type_def, dict)
                else None
            )

            if is_array:
                # Validate array
                if not isinstance(value, list):
                    errors.append(
                        ValidationError(
                            path=path,
                            message="Expected array",
                            expected="array",
                            actual=type(value).__name__,
                        )
                    )
                else:
                    # Validate each element
                    for i, item in enumerate(value):
                        item_path = f"{path}[{i}]"

                        if profile_ref:
                            # Nested profile reference
                            errors.extend(
                                self._validate_nested_profile(item, profile_ref, item_path)
                            )
                        elif opc_type:
                            errors.extend(
                                self._validate_opc_type(item, opc_type, item_path)
                            )
            else:
                # Single value
                if profile_ref:
                    errors.extend(
                        self._validate_nested_profile(value, profile_ref, path)
                    )
                elif opc_type:
                    errors.extend(self._validate_opc_type(value, opc_type, path))

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_payload(
    payload: dict[str, Any],
    profile: dict[str, Any] | str | Path,
    referenced_profiles: dict[str, dict] | None = None,
) -> ValidationResult:
    """
    Convenience function to validate a payload against a profile.

    Args:
        payload: The payload to validate
        profile: Profile dict, file path, or URL
        referenced_profiles: Dict mapping namespace URIs to profile dicts for nested types

    Returns:
        ValidationResult with valid flag and any errors
    """
    if isinstance(profile, (str, Path)):
        profile = load_profile(profile)

    validator = ProfileValidator(profile, referenced_profiles)
    return validator.validate(payload)
