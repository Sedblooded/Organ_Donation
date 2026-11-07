from datetime import datetime
import db_conn


def record_transplant(
    organ_id: int,
    recipient_id: int,
    hosp_id: int,
    lead_doctor_id: int,
    transplant_date: datetime,
    outcome: str = "pending"
) -> int:
    """
    Atomic transaction to record a transplant.
    Locks the organ row with FOR UPDATE.
    The database triggers validate all rules (C1-C6, C10) and automatically
    propagate status to organ ('transplanted') and waitlist ('fulfilled').
    """
    with db_conn.transaction() as conn:
        with conn.cursor() as cur:
            # Concurrency control: row-lock the organ
            cur.execute("SELECT status FROM organ WHERE organ_id = %s FOR UPDATE;", (organ_id,))
            org = cur.fetchone()
            if not org:
                raise ValueError(f"Organ #{organ_id} does not exist.")
            if org[0] not in ('available', 'allocated'):
                raise ValueError(f"Organ #{organ_id} is already {org[0]}.")

            # Insert transplant record
            cur.execute(
                """
                INSERT INTO transplant (organ_id, recipient_id, hosp_id, lead_doctor_id, transplant_date, outcome)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING transplant_id;
                """,
                (organ_id, recipient_id, hosp_id, lead_doctor_id, transplant_date, outcome)
            )
            transplant_id = cur.fetchone()[0]
            return transplant_id


def get_transplants(hosp_id: int = None, outcome_filter: str = "All", start_date=None, end_date=None):
    """Fetch transplant history with all relevant joins."""
    conditions = ["1=1"]
    params = []

    if hosp_id:
        conditions.append("t.hosp_id = %s")
        params.append(hosp_id)

    if outcome_filter and outcome_filter != "All":
        conditions.append("t.outcome = %s")
        params.append(outcome_filter)

    if start_date:
        conditions.append("t.transplant_date >= %s")
        params.append(start_date)

    if end_date:
        conditions.append("t.transplant_date <= %s")
        params.append(end_date)

    query = f"""
    SELECT
        t.transplant_id,
        t.organ_id,
        ot.organ_name,
        o.full_or_part,
        dp.patient_id AS donor_id,
        dp.name AS donor_name,
        dp.blood_group AS donor_blood_group,
        t.recipient_id,
        rp.name AS recipient_name,
        rp.blood_group AS recipient_blood_group,
        t.hosp_id,
        h.name AS hospital_name,
        t.lead_doctor_id,
        doc.name AS lead_doctor_name,
        t.transplant_date,
        t.outcome
    FROM transplant t
    JOIN organ o ON o.organ_id = t.organ_id
    JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
    JOIN donor d ON d.patient_id = o.donor_id
    JOIN patient dp ON dp.patient_id = d.patient_id
    JOIN recipient r ON r.patient_id = t.recipient_id
    JOIN patient rp ON rp.patient_id = r.patient_id
    JOIN hospital h ON h.hosp_id = t.hosp_id
    JOIN doctor doc ON doc.doctor_id = t.lead_doctor_id
    WHERE {' AND '.join(conditions)}
    ORDER BY t.transplant_date DESC;
    """
    return db_conn.fetch_all(query, tuple(params))


def get_transplant_details(transplant_id: int):
    """Retrieve full details for a single transplant."""
    query = """
    SELECT
        t.transplant_id,
        t.organ_id,
        ot.organ_name,
        o.full_or_part,
        dp.patient_id AS donor_id,
        dp.name AS donor_name,
        dp.blood_group AS donor_blood_group,
        t.recipient_id,
        rp.name AS recipient_name,
        rp.blood_group AS recipient_blood_group,
        t.hosp_id,
        h.name AS hospital_name,
        t.lead_doctor_id,
        doc.name AS lead_doctor_name,
        t.transplant_date,
        t.outcome
    FROM transplant t
    JOIN organ o ON o.organ_id = t.organ_id
    JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
    JOIN donor d ON d.patient_id = o.donor_id
    JOIN patient dp ON dp.patient_id = d.patient_id
    JOIN recipient r ON r.patient_id = t.recipient_id
    JOIN patient rp ON rp.patient_id = r.patient_id
    JOIN hospital h ON h.hosp_id = t.hosp_id
    JOIN doctor doc ON doc.doctor_id = t.lead_doctor_id
    WHERE t.transplant_id = %s;
    """
    return db_conn.fetch_one(query, (transplant_id,))
