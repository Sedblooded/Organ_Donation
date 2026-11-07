from datetime import datetime
import db_conn
from utils.rules import calculate_viability


def run_expire_organs() -> int:
    """Trigger the stored expire_organs() procedure to update status in DB."""
    try:
        res = db_conn.execute_returning("SELECT expire_organs() AS expired_count;")
        return res.get("expired_count", 0) if res else 0
    except Exception:
        return 0


def get_organ_types():
    """Fetch all configured organ types."""
    return db_conn.fetch_all("SELECT organ_type_id, organ_name, viability_hours, living_donation_allowed FROM organ_type ORDER BY organ_name;")


def add_organ_type(organ_name: str, viability_hours: int = None, living_donation_allowed: bool = False):
    """Insert a new organ type."""
    query = """
    INSERT INTO organ_type (organ_name, viability_hours, living_donation_allowed)
    VALUES (%s, %s, %s);
    """
    return db_conn.execute(query, (organ_name, viability_hours, living_donation_allowed))


def update_organ_type(organ_type_id: int, organ_name: str, viability_hours: int = None, living_donation_allowed: bool = False):
    """Update an existing organ type."""
    query = """
    UPDATE organ_type
    SET organ_name = %s, viability_hours = %s, living_donation_allowed = %s
    WHERE organ_type_id = %s;
    """
    return db_conn.execute(query, (organ_name, viability_hours, living_donation_allowed, organ_type_id))


def get_consented_donors():
    """Fetch all donors eligible to donate (consent_status = 'given')."""
    query = """
    SELECT
        d.patient_id,
        p.name,
        p.blood_group,
        d.donor_type,
        d.alive_status,
        h.name AS hospital_name
    FROM donor d
    JOIN patient p ON p.patient_id = d.patient_id
    JOIN hospital h ON h.hosp_id = p.hosp_id
    WHERE d.consent_status = 'given'
    ORDER BY p.name;
    """
    return db_conn.fetch_all(query)


def add_organ(organ_type_id: int, donor_id: int, full_or_part: str, harvest_datetime: datetime, description: str = None) -> int:
    """Insert a newly harvested organ."""
    query = """
    INSERT INTO organ (organ_type_id, donor_id, full_or_part, harvest_datetime, status, description)
    VALUES (%s, %s, %s, %s, 'available', %s)
    RETURNING organ_id;
    """
    row = db_conn.execute_returning(query, (organ_type_id, donor_id, full_or_part, harvest_datetime, description or None))
    return row["organ_id"]


def get_organs(status_filter: str = "All", organ_type_id: int = None):
    """Fetch organs with computed viability and joined donor/hospital details."""
    run_expire_organs()

    conditions = ["1=1"]
    params = []

    if status_filter and status_filter != "All":
        conditions.append("o.status = %s")
        params.append(status_filter)

    if organ_type_id:
        conditions.append("o.organ_type_id = %s")
        params.append(organ_type_id)

    query = f"""
    SELECT
        o.organ_id,
        o.organ_type_id,
        ot.organ_name,
        ot.viability_hours,
        ot.living_donation_allowed,
        o.donor_id,
        dp.name AS donor_name,
        dp.blood_group,
        d.donor_type,
        o.full_or_part,
        o.harvest_datetime,
        o.status,
        o.description,
        h.name AS hospital_name
    FROM organ o
    JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
    JOIN donor d ON d.patient_id = o.donor_id
    JOIN patient dp ON dp.patient_id = d.patient_id
    JOIN hospital h ON h.hosp_id = dp.hosp_id
    WHERE {' AND '.join(conditions)}
    ORDER BY o.organ_id DESC;
    """
    rows = db_conn.fetch_all(query, tuple(params))

    # Add calculated remaining time & viability badge
    for r in rows:
        hours_rem, is_exp, label = calculate_viability(r["harvest_datetime"], r["viability_hours"])
        r["hours_remaining"] = hours_rem
        r["is_expired"] = is_exp
        r["viability_label"] = label

    return rows


def get_available_organs():
    """Fetch organs that are currently available for allocation/matching."""
    return get_organs(status_filter="available")
