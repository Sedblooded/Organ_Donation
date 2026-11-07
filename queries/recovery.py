import datetime
import db_conn


def add_recovery_checkup(transplant_id: int, doctor_id: int, checkup_date: datetime.date, status: str, description: str = None) -> int:
    """Insert a recovery checkup record."""
    query = """
    INSERT INTO recovery (transplant_id, doctor_id, checkup_date, status, description)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING recovery_id;
    """
    row = db_conn.execute_returning(query, (transplant_id, doctor_id, checkup_date, status, description or None))
    return row["recovery_id"]


def get_recoveries_for_transplant(transplant_id: int):
    """Fetch chronological list of checkups for a given transplant."""
    query = """
    SELECT
        r.recovery_id,
        r.transplant_id,
        r.doctor_id,
        d.name AS doctor_name,
        r.checkup_date,
        r.status,
        r.description
    FROM recovery r
    JOIN doctor d ON d.doctor_id = r.doctor_id
    WHERE r.transplant_id = %s
    ORDER BY r.checkup_date ASC, r.recovery_id ASC;
    """
    return db_conn.fetch_all(query, (transplant_id,))


def get_all_recoveries(hosp_id: int = None, status_filter: str = "All"):
    """Fetch all recovery checkups with joined transplant and patient info."""
    conditions = ["1=1"]
    params = []

    if hosp_id:
        conditions.append("t.hosp_id = %s")
        params.append(hosp_id)

    if status_filter and status_filter != "All":
        conditions.append("r.status = %s")
        params.append(status_filter)

    query = f"""
    SELECT
        r.recovery_id,
        r.transplant_id,
        ot.organ_name,
        rp.name AS recipient_name,
        h.name AS hospital_name,
        doc.name AS doctor_name,
        r.checkup_date,
        r.status,
        r.description
    FROM recovery r
    JOIN transplant t ON t.transplant_id = r.transplant_id
    JOIN organ o ON o.organ_id = t.organ_id
    JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
    JOIN recipient rec ON rec.patient_id = t.recipient_id
    JOIN patient rp ON rp.patient_id = rec.patient_id
    JOIN hospital h ON h.hosp_id = t.hosp_id
    JOIN doctor doc ON doc.doctor_id = r.doctor_id
    WHERE {' AND '.join(conditions)}
    ORDER BY r.checkup_date DESC;
    """
    return db_conn.fetch_all(query, tuple(params))
