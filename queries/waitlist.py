import datetime
import db_conn


def get_active_recipients():
    """Fetch recipients list for waitlist entry."""
    query = """
    SELECT
        r.patient_id,
        p.name,
        p.blood_group,
        r.urgency_level,
        h.name AS hospital_name,
        h.hosp_id
    FROM recipient r
    JOIN patient p ON p.patient_id = r.patient_id
    JOIN hospital h ON h.hosp_id = p.hosp_id
    ORDER BY p.name;
    """
    return db_conn.fetch_all(query)


def check_active_waitlist_exists(recipient_id: int, organ_type_id: int) -> bool:
    """Check if recipient already has an active waitlist entry for this organ type."""
    query = """
    SELECT 1 FROM waitlist
    WHERE recipient_id = %s AND organ_type_id = %s AND status = 'active';
    """
    res = db_conn.fetch_one(query, (recipient_id, organ_type_id))
    return bool(res)


def add_to_waitlist(recipient_id: int, organ_type_id: int, hosp_id: int, priority: int, date_added: datetime.date = None) -> int:
    """Add a recipient to the waitlist."""
    if date_added is None:
        date_added = datetime.date.today()

    query = """
    INSERT INTO waitlist (recipient_id, organ_type_id, hosp_id, priority, date_added, status)
    VALUES (%s, %s, %s, %s, %s, 'active')
    RETURNING waitlist_id;
    """
    row = db_conn.execute_returning(query, (recipient_id, organ_type_id, hosp_id, priority, date_added))
    return row["waitlist_id"]


def get_waitlist(status_filter: str = "active", organ_type_id: int = None, hosp_id: int = None):
    """Retrieve waitlist entries sorted by priority, urgency, and date_added."""
    conditions = ["1=1"]
    params = []

    if status_filter and status_filter != "All":
        conditions.append("w.status = %s")
        params.append(status_filter)

    if organ_type_id:
        conditions.append("w.organ_type_id = %s")
        params.append(organ_type_id)

    if hosp_id:
        conditions.append("w.hosp_id = %s")
        params.append(hosp_id)

    query = f"""
    SELECT
        w.waitlist_id,
        w.recipient_id,
        p.name AS recipient_name,
        p.blood_group,
        r.urgency_level,
        w.organ_type_id,
        ot.organ_name,
        w.priority,
        w.date_added,
        CURRENT_DATE - w.date_added AS days_waiting,
        w.status,
        w.hosp_id,
        h.name AS hospital_name
    FROM waitlist w
    JOIN recipient r ON r.patient_id = w.recipient_id
    JOIN patient p ON p.patient_id = r.patient_id
    JOIN organ_type ot ON ot.organ_type_id = w.organ_type_id
    JOIN hospital h ON h.hosp_id = w.hosp_id
    WHERE {' AND '.join(conditions)}
    ORDER BY w.priority ASC, r.urgency_level ASC, w.date_added ASC;
    """
    return db_conn.fetch_all(query, tuple(params))


def update_waitlist_priority(waitlist_id: int, new_priority: int):
    """Change priority for an active waitlist entry."""
    return db_conn.execute("UPDATE waitlist SET priority = %s WHERE waitlist_id = %s;", (new_priority, waitlist_id))


def update_waitlist_status(waitlist_id: int, new_status: str):
    """Update status of a waitlist entry (e.g. 'removed' to cancel)."""
    return db_conn.execute("UPDATE waitlist SET status = %s WHERE waitlist_id = %s;", (new_status, waitlist_id))
