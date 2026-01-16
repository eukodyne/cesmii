#!/usr/bin/env python3
"""
Example: Validate a Work Order payload against CESMII SM Profiles.

This example demonstrates how to:
1. Load profiles from local files or URLs
2. Validate a payload with nested profile references
3. Handle validation results
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))

from cesmii_validator import ProfileValidator, load_profile, validate_payload


def main():
    # Paths to profiles (adjust as needed)
    # Can also use URLs like:
    # "https://raw.githubusercontent.com/eukodyne/cesmii/main/smprofiles/WorkOrderV1.jsonld"

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent  # Go up to eukodyne directory

    workorder_profile_path = project_root / "smprofiles" / "WorkOrderV1.jsonld"
    feedingredient_profile_path = project_root / "smprofiles" / "FeedIngredientV1.jsonld"
    payload_path = script_dir / "sample_payload.json"

    print("CESMII SM Profile Validator - Work Order Example")
    print("=" * 50)

    # Load profiles
    print(f"\nLoading WorkOrderV1 profile from: {workorder_profile_path}")
    workorder_profile = load_profile(workorder_profile_path)

    print(f"Loading FeedIngredientV1 profile from: {feedingredient_profile_path}")
    feedingredient_profile = load_profile(feedingredient_profile_path)

    # Load payload
    print(f"Loading payload from: {payload_path}")
    with open(payload_path) as f:
        payload = json.load(f)

    # Create referenced profiles dict for nested validation
    referenced_profiles = {
        "https://www.github.com/eukodyne/cesmii/smprofiles/FeedIngredientV1": feedingredient_profile,
    }

    # Validate
    print("\nValidating payload...")
    print("-" * 50)

    result = validate_payload(
        payload=payload,
        profile=workorder_profile,
        referenced_profiles=referenced_profiles,
    )

    # Display results
    if result.valid:
        print("✓ Payload is VALID")
    else:
        print(f"✗ Payload is INVALID ({len(result.errors)} errors)")
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    print("\n" + "=" * 50)

    # Return exit code based on validation result
    return 0 if result.valid else 1


def example_with_invalid_payload():
    """Demonstrate validation errors with an invalid payload."""
    print("\n\nExample: Invalid Payload")
    print("=" * 50)

    # Create a payload with errors
    invalid_payload = {
        "$namespace": "https://www.github.com/eukodyne/cesmii/smprofiles/WorkOrderV1",
        "WorkOrderID": "not-a-valid-uuid",  # Invalid GUID format (if we were checking)
        "WorkOrderNumber": "should-be-integer",  # Wrong type
        "TimeZone": {
            "offset": 99999,  # Out of Int16 range
            # Missing daylightSavingInOffset
        },
        "StartTimeLocal": "2026-01-16T08:00:00",  # Valid
        "StartTimeUTC": "2026-01-16T14:00:00",  # Missing Z suffix
        "Quantity": "one hundred",  # Should be number
    }

    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    workorder_profile = load_profile(project_root / "smprofiles" / "WorkOrderV1.jsonld")

    result = validate_payload(invalid_payload, workorder_profile)

    print(f"\nValidation result: {'VALID' if result.valid else 'INVALID'}")
    if result.errors:
        print(f"\nFound {len(result.errors)} errors:")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    exit_code = main()
    example_with_invalid_payload()
    sys.exit(exit_code)
