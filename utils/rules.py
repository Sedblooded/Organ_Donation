from datetime import datetime, timezone
from typing import Optional, Tuple

ORGAN_STATUS = ["available", "allocated", "transplanted", "expired"]
WAITLIST_STATUS = ["active", "matched", "removed", "fulfilled"]
TRANSPLANT_OUTCOME = ["successful", "complications", "failed", "pending"]
RECOVERY_STATUS = ["stable", "improving", "critical", "rejected", "recovered", "deceased"]
DONOR_CONSENT_STATUS = ["pending", "given", "withdrawn"]
DONOR_TYPE = ["living", "deceased"]
ALIVE_STATUS = ["alive", "deceased"]
GENDERS = ["M", "F", "Other"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
FACILITY_TYPES = ["transplant_centre", "general", "clinic"]

# Donor Blood Group -> Compatible Recipient Blood Groups
BLOOD_COMPATIBILITY = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}


def is_blood_compatible(donor_bg: str, recipient_bg: str) -> bool:
    """Check if donor blood group can donate to recipient."""
    return recipient_bg in BLOOD_COMPATIBILITY.get(donor_bg, [])


def calculate_viability(harvest_datetime: datetime, viability_hours: Optional[int]) -> Tuple[Optional[float], bool, str]:
    """
    Calculate remaining viability for an organ.
    Returns: (hours_remaining, is_expired, human_readable_label)
    If viability_hours is None, the organ is storable indefinitely.
    """
    if viability_hours is None:
        return None, False, "Storable (No Expiry)"

    now = datetime.now(timezone.utc)
    if harvest_datetime.tzinfo is None:
        # If naive, treat as UTC
        harvest_dt = harvest_datetime.replace(tzinfo=timezone.utc)
    else:
        harvest_dt = harvest_datetime

    elapsed_seconds = (now - harvest_dt).total_seconds()
    total_viability_seconds = viability_hours * 3600
    remaining_seconds = total_viability_seconds - elapsed_seconds
    remaining_hours = remaining_seconds / 3600

    if remaining_seconds <= 0:
        return remaining_hours, True, f"Expired ({abs(remaining_hours):.1f}h ago)"
    elif remaining_hours < 1:
        return remaining_hours, False, f"{int(remaining_seconds // 60)}m left"
    else:
        return remaining_hours, False, f"{remaining_hours:.1f}h left"
