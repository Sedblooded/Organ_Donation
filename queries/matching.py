import db_conn
from queries.organs import run_expire_organs
from utils.rules import calculate_viability


def get_available_organs_for_matching():
    """Retrieve available non-expired organs ready for recipient matching."""
    run_expire_organs()
    query = """
    SELECT
        o.organ_id,
        ot.organ_name,
        o.full_or_part,
        dp.name AS donor_name,
        dp.blood_group AS donor_blood_group,
        o.harvest_datetime,
        ot.viability_hours,
        h.name AS donor_hospital
    FROM organ o
    JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
    JOIN donor d ON d.patient_id = o.donor_id
    JOIN patient dp ON dp.patient_id = d.patient_id
    JOIN hospital h ON h.hosp_id = dp.hosp_id
    WHERE o.status = 'available'
    ORDER BY o.harvest_datetime ASC;
    """
    rows = db_conn.fetch_all(query)
    for r in rows:
        rem_hours, is_exp, label = calculate_viability(r["harvest_datetime"], r["viability_hours"])
        r["hours_remaining"] = rem_hours
        r["is_expired"] = is_exp
        r["viability_label"] = label
    return rows


def find_matches_for_organ(organ_id: int):
    """Call the SQL stored procedure find_matches(organ_id)."""
    run_expire_organs()
    query = """
    SELECT
        m.rank,
        m.waitlist_id,
        m.recipient_id,
        m.recipient_name,
        m.blood_group,
        m.priority,
        m.urgency_level,
        m.waiting_since,
        CURRENT_DATE - m.waiting_since AS days_waiting,
        m.listed_at_hospital
    FROM find_matches(%s) m;
    """
    return db_conn.fetch_all(query, (organ_id,))


def get_organ_summary(organ_id: int):
    """Fetch quick details for the selected organ."""
    query = """
    SELECT
        o.organ_id,
        ot.organ_name,
        o.full_or_part,
        dp.patient_id AS donor_id,
        dp.name AS donor_name,
        dp.blood_group AS donor_blood_group,
        o.harvest_datetime,
        ot.viability_hours,
        o.status,
        h.name AS donor_hospital
    FROM organ o
    JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
    JOIN donor d ON d.patient_id = o.donor_id
    JOIN patient dp ON dp.patient_id = d.patient_id
    JOIN hospital h ON h.hosp_id = dp.hosp_id
    WHERE o.organ_id = %s;
    """
    row = db_conn.fetch_one(query, (organ_id,))
    if row:
        rem_hours, is_exp, label = calculate_viability(row["harvest_datetime"], row["viability_hours"])
        row["hours_remaining"] = rem_hours
        row["is_expired"] = is_exp
        row["viability_label"] = label
    return row
