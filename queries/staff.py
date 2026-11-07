import datetime
import db_conn


# ==============================================================================
# HOSPITALS
# ==============================================================================

def get_hospitals():
    """Fetch all registered hospitals."""
    query = """
    SELECT h.hosp_id, h.reg_id, h.name, h.facility_type, h.street, h.pincode, pa.city, pa.state, h.contact
    FROM hospital h
    LEFT JOIN pincode_area pa ON pa.pincode = h.pincode
    ORDER BY h.name;
    """
    return db_conn.fetch_all(query)


def get_transplant_centres():
    """Fetch only hospitals designated as transplant centres (required for rule C6)."""
    query = """
    SELECT h.hosp_id, h.reg_id, h.name, h.facility_type, h.street, h.pincode, pa.city, pa.state, h.contact
    FROM hospital h
    LEFT JOIN pincode_area pa ON pa.pincode = h.pincode
    WHERE h.facility_type = 'transplant_centre'
    ORDER BY h.name;
    """
    return db_conn.fetch_all(query)


def add_hospital(reg_id: str, name: str, facility_type: str, street: str, pincode: str, contact: str = None) -> int:
    """Insert a new hospital."""
    query = """
    INSERT INTO hospital (reg_id, name, facility_type, street, pincode, contact)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING hosp_id;
    """
    row = db_conn.execute_returning(query, (reg_id, name, facility_type, street or None, pincode, contact or None))
    return row["hosp_id"]


# ==============================================================================
# DOCTORS
# ==============================================================================

def get_doctors():
    """Fetch all doctors with their specializations aggregated."""
    query = """
    SELECT
        d.doctor_id,
        d.med_bar_id,
        d.general_id,
        d.name,
        d.contact,
        COALESCE(STRING_AGG(DISTINCT s.spec_name, ', '), 'None') AS specializations,
        COALESCE(STRING_AGG(DISTINCT h.name, ', '), 'None') AS affiliated_hospitals
    FROM doctor d
    LEFT JOIN doctor_spec ds ON ds.doctor_id = d.doctor_id
    LEFT JOIN specialization s ON s.spec_id = ds.spec_id
    LEFT JOIN doctor_hospital dh ON dh.doctor_id = d.doctor_id
    LEFT JOIN hospital h ON h.hosp_id = dh.hosp_id
    GROUP BY d.doctor_id, d.med_bar_id, d.general_id, d.name, d.contact
    ORDER BY d.name;
    """
    return db_conn.fetch_all(query)


def add_doctor(med_bar_id: str, general_id: str, name: str, contact: str = None) -> int:
    """Insert a new doctor."""
    query = """
    INSERT INTO doctor (med_bar_id, general_id, name, contact)
    VALUES (%s, %s, %s, %s)
    RETURNING doctor_id;
    """
    row = db_conn.execute_returning(query, (med_bar_id, general_id, name, contact or None))
    return row["doctor_id"]


def get_doctors_affiliated_with_hospital(hosp_id: int):
    """Fetch doctors affiliated with a specific hospital (needed for lead surgeon selection)."""
    query = """
    SELECT d.doctor_id, d.name, d.med_bar_id, dh.role
    FROM doctor d
    JOIN doctor_hospital dh ON dh.doctor_id = d.doctor_id
    WHERE dh.hosp_id = %s
    ORDER BY d.name;
    """
    return db_conn.fetch_all(query, (hosp_id,))


# ==============================================================================
# SPECIALIZATIONS
# ==============================================================================

def get_specializations():
    """Fetch all specializations."""
    return db_conn.fetch_all("SELECT spec_id, spec_name FROM specialization ORDER BY spec_name;")


def add_specialization(spec_name: str) -> int:
    """Insert a new specialization."""
    query = "INSERT INTO specialization (spec_name) VALUES (%s) RETURNING spec_id;"
    row = db_conn.execute_returning(query, (spec_name,))
    return row["spec_id"]


def get_doctor_specializations(doctor_id: int):
    """Fetch specialization IDs for a given doctor."""
    query = "SELECT spec_id FROM doctor_spec WHERE doctor_id = %s;"
    rows = db_conn.fetch_all(query, (doctor_id,))
    return [r["spec_id"] for r in rows]


def set_doctor_specializations(doctor_id: int, spec_ids: list):
    """Set the specializations for a doctor (replaces existing)."""
    with db_conn.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM doctor_spec WHERE doctor_id = %s;", (doctor_id,))
            for s_id in spec_ids:
                cur.execute("INSERT INTO doctor_spec (doctor_id, spec_id) VALUES (%s, %s);", (doctor_id, s_id))


# ==============================================================================
# AFFILIATIONS (doctor_hospital)
# ==============================================================================

def get_affiliations():
    """Fetch all doctor-hospital affiliations."""
    query = """
    SELECT
        dh.doctor_id,
        d.name AS doctor_name,
        d.med_bar_id,
        dh.hosp_id,
        h.name AS hospital_name,
        dh.role,
        dh.join_date
    FROM doctor_hospital dh
    JOIN doctor d ON d.doctor_id = dh.doctor_id
    JOIN hospital h ON h.hosp_id = dh.hosp_id
    ORDER BY h.name, d.name;
    """
    return db_conn.fetch_all(query)


def add_affiliation(doctor_id: int, hosp_id: int, role: str, join_date: datetime.date = None):
    """Add a doctor-hospital affiliation."""
    if join_date is None:
        join_date = datetime.date.today()
    query = """
    INSERT INTO doctor_hospital (doctor_id, hosp_id, role, join_date)
    VALUES (%s, %s, %s, %s);
    """
    return db_conn.execute(query, (doctor_id, hosp_id, role, join_date))
