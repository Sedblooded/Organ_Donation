import db_conn


def get_all_pincodes():
    """Fetch all pincode areas for selectboxes."""
    return db_conn.fetch_all("SELECT pincode, city, state FROM pincode_area ORDER BY city, pincode;")


def insert_pincode(pincode: str, city: str, state: str):
    """Insert a new pincode area."""
    return db_conn.execute(
        "INSERT INTO pincode_area (pincode, city, state) VALUES (%s, %s, %s);",
        (pincode, city, state)
    )


def add_patient(name: str, dob, gender: str, blood_group: str, street: str, pincode: str, notes: str, hosp_id: int) -> int:
    """Insert a new patient and return the patient_id."""
    row = db_conn.execute_returning(
        """
        INSERT INTO patient (name, dob, gender, blood_group, street, pincode, notes, hosp_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING patient_id;
        """,
        (name, dob, gender, blood_group, street, pincode, notes or None, hosp_id)
    )
    return row["patient_id"]


def make_donor(patient_id: int, donor_type: str, alive_status: str, consent_status: str, medical_notes: str):
    """Register an existing patient as a donor."""
    db_conn.execute(
        """
        INSERT INTO donor (patient_id, donor_type, alive_status, consent_status, medical_notes)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (patient_id, donor_type, alive_status, consent_status, medical_notes or None)
    )


def make_recipient(patient_id: int, urgency_level: int, medical_notes: str):
    """Register an existing patient as a recipient."""
    db_conn.execute(
        """
        INSERT INTO recipient (patient_id, urgency_level, medical_notes)
        VALUES (%s, %s, %s);
        """,
        (patient_id, urgency_level, medical_notes or None)
    )


def register_full_patient(
    name: str, dob, gender: str, blood_group: str, street: str, pincode: str, notes: str, hosp_id: int,
    role_type: str = "None",  # "None", "Donor", "Recipient", "Both"
    donor_type: str = "deceased", alive_status: str = "deceased", consent_status: str = "pending", donor_notes: str = "",
    urgency_level: int = 3, recipient_notes: str = ""
) -> int:
    """Atomic transaction to register patient and optional donor/recipient roles."""
    with db_conn.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO patient (name, dob, gender, blood_group, street, pincode, notes, hosp_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING patient_id;
                """,
                (name, dob, gender, blood_group, street, pincode, notes or None, hosp_id)
            )
            patient_id = cur.fetchone()[0]

            if role_type in ("Donor", "Both"):
                cur.execute(
                    """
                    INSERT INTO donor (patient_id, donor_type, alive_status, consent_status, medical_notes)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (patient_id, donor_type, alive_status, consent_status, donor_notes or None)
                )

            if role_type in ("Recipient", "Both"):
                cur.execute(
                    """
                    INSERT INTO recipient (patient_id, urgency_level, medical_notes)
                    VALUES (%s, %s, %s);
                    """,
                    (patient_id, urgency_level, recipient_notes or None)
                )

            return patient_id


def get_patients_not_donors():
    """Fetch patients who are not yet registered as donors."""
    query = """
    SELECT p.patient_id, p.name, p.blood_group, p.dob, h.name AS hospital_name
    FROM patient p
    JOIN hospital h ON h.hosp_id = p.hosp_id
    WHERE NOT EXISTS (SELECT 1 FROM donor d WHERE d.patient_id = p.patient_id)
    ORDER BY p.name;
    """
    return db_conn.fetch_all(query)


def get_patients_not_recipients():
    """Fetch patients who are not yet registered as recipients."""
    query = """
    SELECT p.patient_id, p.name, p.blood_group, p.dob, h.name AS hospital_name
    FROM patient p
    JOIN hospital h ON h.hosp_id = p.hosp_id
    WHERE NOT EXISTS (SELECT 1 FROM recipient r WHERE r.patient_id = p.patient_id)
    ORDER BY p.name;
    """
    return db_conn.fetch_all(query)


def search_patients(name_search: str = None, blood_group: str = None, hosp_id: int = None, role_filter: str = "All"):
    """Search patients with joined donor and recipient flags."""
    conditions = ["1=1"]
    params = []

    if name_search:
        conditions.append("p.name ILIKE %s")
        params.append(f"%{name_search}%")
    if blood_group and blood_group != "All":
        conditions.append("p.blood_group = %s")
        params.append(blood_group)
    if hosp_id:
        conditions.append("p.hosp_id = %s")
        params.append(hosp_id)

    if role_filter == "Donor":
        conditions.append("d.patient_id IS NOT NULL")
    elif role_filter == "Recipient":
        conditions.append("r.patient_id IS NOT NULL")

    query = f"""
    SELECT
        p.patient_id,
        p.name,
        p.dob,
        p.gender,
        p.blood_group,
        p.street,
        p.pincode,
        pa.city,
        pa.state,
        p.hosp_id,
        h.name AS hospital_name,
        p.notes,
        CASE WHEN d.patient_id IS NOT NULL THEN 'Yes' ELSE 'No' END AS is_donor,
        d.donor_type,
        d.alive_status,
        d.consent_status,
        d.medical_notes AS donor_notes,
        CASE WHEN r.patient_id IS NOT NULL THEN 'Yes' ELSE 'No' END AS is_recipient,
        r.urgency_level,
        r.medical_notes AS recipient_notes
    FROM patient p
    JOIN hospital h ON h.hosp_id = p.hosp_id
    LEFT JOIN pincode_area pa ON pa.pincode = p.pincode
    LEFT JOIN donor d ON d.patient_id = p.patient_id
    LEFT JOIN recipient r ON r.patient_id = p.patient_id
    WHERE {' AND '.join(conditions)}
    ORDER BY p.patient_id DESC;
    """
    return db_conn.fetch_all(query, tuple(params))


def update_patient(patient_id: int, name: str, dob, gender: str, blood_group: str, street: str, pincode: str, notes: str, hosp_id: int):
    """Update patient core details."""
    query = """
    UPDATE patient
    SET name = %s, dob = %s, gender = %s, blood_group = %s, street = %s, pincode = %s, notes = %s, hosp_id = %s
    WHERE patient_id = %s;
    """
    return db_conn.execute(query, (name, dob, gender, blood_group, street, pincode, notes or None, hosp_id, patient_id))


def delete_patient(patient_id: int):
    """Delete a patient (fails if referenced by FK)."""
    return db_conn.execute("DELETE FROM patient WHERE patient_id = %s;", (patient_id,))
