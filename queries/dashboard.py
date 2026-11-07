import db_conn


def get_summary_metrics():
    """Fetch 6 key headline metrics for the dashboard."""
    query = """
    SELECT
        (SELECT COUNT(*) FROM donor) AS total_donors,
        (SELECT COUNT(*) FROM recipient) AS total_recipients,
        (SELECT COUNT(*) FROM organ WHERE status = 'available') AS available_organs,
        (SELECT COUNT(*) FROM waitlist WHERE status = 'active') AS active_waitlist,
        (SELECT COUNT(*) FROM transplant) AS total_transplants,
        (SELECT COUNT(*) FROM transplant WHERE outcome = 'successful') AS successful_transplants;
    """
    row = db_conn.fetch_one(query) or {}
    total_tx = row.get("total_transplants", 0)
    succ_tx = row.get("successful_transplants", 0)
    success_rate = (succ_tx / total_tx * 100) if total_tx > 0 else 0.0

    return {
        "total_donors": row.get("total_donors", 0),
        "total_recipients": row.get("total_recipients", 0),
        "available_organs": row.get("available_organs", 0),
        "active_waitlist": row.get("active_waitlist", 0),
        "total_transplants": total_tx,
        "success_rate": round(success_rate, 1)
    }


def get_waitlist_by_organ_type():
    """Count of active waitlist requests grouped by organ type."""
    query = """
    SELECT ot.organ_name, COUNT(w.waitlist_id) AS count
    FROM organ_type ot
    LEFT JOIN waitlist w ON w.organ_type_id = ot.organ_type_id AND w.status = 'active'
    GROUP BY ot.organ_name
    ORDER BY count DESC, ot.organ_name;
    """
    return db_conn.fetch_all(query)


def get_transplants_by_hospital():
    """Count of transplants per hospital."""
    query = """
    SELECT h.name AS hospital_name, COUNT(t.transplant_id) AS transplant_count
    FROM hospital h
    JOIN transplant t ON t.hosp_id = h.hosp_id
    GROUP BY h.name
    ORDER BY transplant_count DESC;
    """
    return db_conn.fetch_all(query)


def get_transplant_outcomes():
    """Breakdown of transplant outcomes."""
    query = """
    SELECT outcome, COUNT(*) AS count
    FROM transplant
    GROUP BY outcome
    ORDER BY count DESC;
    """
    return db_conn.fetch_all(query)


def get_transplants_per_month():
    """Transplants over time by month."""
    query = """
    SELECT TO_CHAR(transplant_date, 'YYYY-MM') AS month, COUNT(*) AS count
    FROM transplant
    GROUP BY TO_CHAR(transplant_date, 'YYYY-MM')
    ORDER BY month ASC;
    """
    return db_conn.fetch_all(query)


def get_expiring_organs(max_hours: int = 24):
    """Perishable available organs expiring within max_hours."""
    query = """
    SELECT
        o.organ_id,
        ot.organ_name,
        p.name AS donor_name,
        p.blood_group,
        o.harvest_datetime,
        ot.viability_hours,
        ROUND(
            EXTRACT(EPOCH FROM ((o.harvest_datetime + make_interval(hours => ot.viability_hours)) - NOW())) / 3600.0,
            1
        ) AS hours_left
    FROM organ o
    JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
    JOIN patient p ON p.patient_id = o.donor_id
    WHERE o.status = 'available'
      AND ot.viability_hours IS NOT NULL
      AND (o.harvest_datetime + make_interval(hours => ot.viability_hours)) > NOW()
      AND (o.harvest_datetime + make_interval(hours => ot.viability_hours)) <= NOW() + make_interval(hours => %s)
    ORDER BY hours_left ASC;
    """
    return db_conn.fetch_all(query, (max_hours,))


def get_latest_transplants(limit: int = 10):
    """Latest transplants with joined patient and doctor details."""
    query = """
    SELECT
        t.transplant_id,
        ot.organ_name,
        dp.name AS donor_name,
        rp.name AS recipient_name,
        h.name AS hospital_name,
        doc.name AS lead_doctor,
        t.transplant_date,
        t.outcome
    FROM transplant t
    JOIN organ o ON o.organ_id = t.organ_id
    JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
    JOIN patient dp ON dp.patient_id = o.donor_id
    JOIN patient rp ON rp.patient_id = t.recipient_id
    JOIN hospital h ON h.hosp_id = t.hosp_id
    JOIN doctor doc ON doc.doctor_id = t.lead_doctor_id
    ORDER BY t.transplant_date DESC
    LIMIT %s;
    """
    return db_conn.fetch_all(query, (limit,))


def get_latest_recoveries(limit: int = 10):
    """Latest recovery checkups."""
    query = """
    SELECT
        r.recovery_id,
        r.transplant_id,
        rp.name AS patient_name,
        doc.name AS doctor_name,
        r.checkup_date,
        r.status,
        r.description
    FROM recovery r
    JOIN transplant t ON t.transplant_id = r.transplant_id
    JOIN patient rp ON rp.patient_id = t.recipient_id
    JOIN doctor doc ON doc.doctor_id = r.doctor_id
    ORDER BY r.checkup_date DESC
    LIMIT %s;
    """
    return db_conn.fetch_all(query, (limit,))
