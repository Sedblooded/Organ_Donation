"""Health checks for the organ-transplant database. Safe to run at ANY time.

    python check_db.py            # schema + data invariants + rule tests
    python check_db.py --seed     # also verify the mock-data row counts

What it does
  1. SCHEMA      all tables, triggers and functions exist.
  2. INVARIANTS  read-only queries over your REAL data; each must return 0 bad rows
                 (e.g. no transplant with incompatible blood groups).
  3. RULE TESTS  tries to break every rule using its own throw-away fixtures, inside a
                 transaction that is ROLLED BACK. Your data is never modified.

Use it from code:   from check_db import run_all_checks;  ok = run_all_checks(conn)
Exit code: 0 = everything fine, 1 = something is broken.
"""

import argparse
import sys
import uuid

import psycopg2 

from db import get_connection 

EXPECTED_TABLES = [
    "pincode_area",
    "blood_compat",
    "hospital",
    "specialization",
    "doctor",
    "doctor_spec",
    "doctor_hospital",
    "patient",
    "donor",
    "recipient",
    "organ_type",
    "organ",
    "waitlist",
    "transplant",
    "recovery",
]
EXPECTED_TRIGGERS = {  # trigger name -> table
    "organ_validate": "organ",
    "transplant_validate": "transplant",
    "transplant_after": "transplant",
    "donor_guard": "donor",
    "recovery_validate": "recovery",
}
EXPECTED_FUNCTIONS = ["find_matches", "expire_organs"]
SEED_COUNTS = {  # row counts right after seed_db.py
    "pincode_area": 10,
    "blood_compat": 27,
    "hospital": 6,
    "specialization": 7,
    "doctor": 8,
    "doctor_spec": 14,
    "doctor_hospital": 10,
    "patient": 19,
    "donor": 9,
    "recipient": 10,
    "organ_type": 6,
    "organ": 10,
    "waitlist": 11,
    "transplant": 5,
    "recovery": 13,
}


# ---------------------------------------------------------------------------
# tiny report helper
# ---------------------------------------------------------------------------
class Report:
    def __init__(self, verbose=True):
        self.rows, self.verbose = [], verbose

    def add(self, status, name, detail=""):
        self.rows.append((status, name, detail))
        if self.verbose:
            icon = {"PASS": "[ OK ]", "FAIL": "[FAIL]", "WARN": "[WARN]"}[status]
            print(
                f"{icon} {name}"
                + (f"  ->  {detail}" if detail and status != "PASS" else "")
            )

    def section(self, title):
        if self.verbose:
            print(f"\n== {title} " + "=" * max(3, 60 - len(title)))

    @property
    def failed(self):
        return sum(1 for r in self.rows if r[0] == "FAIL")

    def summary(self):
        p = sum(1 for r in self.rows if r[0] == "PASS")
        w = sum(1 for r in self.rows if r[0] == "WARN")
        print(f"\nRESULT: {p} passed, {self.failed} failed, {w} warnings")
        return self.failed == 0


# ---------------------------------------------------------------------------
# 1. schema checks
# ---------------------------------------------------------------------------
def check_schema(cur, rep):
    rep.section("SCHEMA")
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    )
    have = {r[0] for r in cur.fetchall()}
    missing = [t for t in EXPECTED_TABLES if t not in have]
    rep.add(
        "FAIL" if missing else "PASS",
        f"all {len(EXPECTED_TABLES)} tables exist",
        "missing: " + ", ".join(missing),
    )

    cur.execute(
        "SELECT tgname, tgrelid::regclass::text FROM pg_trigger WHERE NOT tgisinternal"
    )
    trig = {r[0]: r[1] for r in cur.fetchall()}
    bad = [f"{n} on {t}" for n, t in EXPECTED_TRIGGERS.items() if trig.get(n) != t]
    rep.add(
        "FAIL" if bad else "PASS",
        f"all {len(EXPECTED_TRIGGERS)} rule triggers exist",
        "missing: " + ", ".join(bad),
    )

    cur.execute(
        "SELECT proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE n.nspname='public'"
    )
    funcs = {r[0] for r in cur.fetchall()}
    bad = [f for f in EXPECTED_FUNCTIONS if f not in funcs]
    rep.add(
        "FAIL" if bad else "PASS",
        "helper functions exist (find_matches, expire_organs)",
        "missing: " + ", ".join(bad),
    )

    cur.execute("SELECT count(*) FROM blood_compat")
    n = cur.fetchone()[0]
    rep.add(
        "PASS" if n == 27 else "FAIL",
        "blood_compat reference table has 27 rows",
        f"found {n}",
    )


def check_seed_counts(cur, rep):
    rep.section("SEED DATA COUNTS")
    for table, expected in SEED_COUNTS.items():
        cur.execute(f"SELECT count(*) FROM {table}")
        n = cur.fetchone()[0]
        rep.add(
            "PASS" if n == expected else "FAIL",
            f"{table}: {expected} rows",
            f"found {n}",
        )


# ---------------------------------------------------------------------------
# 2. data invariants  (each query must return ZERO rows)
# ---------------------------------------------------------------------------
INVARIANTS = [
    (
        "every transplant is blood-group compatible",
        """SELECT t.transplant_id FROM transplant t
          JOIN organ o ON o.organ_id = t.organ_id
          JOIN patient d ON d.patient_id = o.donor_id
          JOIN patient r ON r.patient_id = t.recipient_id
          LEFT JOIN blood_compat bc ON bc.donor_bg = d.blood_group AND bc.recipient_bg = r.blood_group
         WHERE bc.donor_bg IS NULL""",
    ),
    (
        "no transplant has donor = recipient",
        """SELECT t.transplant_id FROM transplant t JOIN organ o ON o.organ_id = t.organ_id
         WHERE o.donor_id = t.recipient_id""",
    ),
    (
        "every transplant happened inside the organ's viability window",
        """SELECT t.transplant_id FROM transplant t
          JOIN organ o ON o.organ_id = t.organ_id
          JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
         WHERE t.transplant_date < o.harvest_datetime
            OR (ot.viability_hours IS NOT NULL
                AND t.transplant_date > o.harvest_datetime + make_interval(hours => ot.viability_hours))""",
    ),
    (
        "every transplant took place at a transplant centre",
        """SELECT t.transplant_id FROM transplant t JOIN hospital h ON h.hosp_id = t.hosp_id
         WHERE h.facility_type <> 'transplant_centre'""",
    ),
    (
        "organ status matches transplant records (transplanted <=> has a transplant)",
        """SELECT o.organ_id FROM organ o LEFT JOIN transplant t ON t.organ_id = o.organ_id
         WHERE (t.transplant_id IS NOT NULL AND o.status <> 'transplanted')
            OR (t.transplant_id IS NULL AND o.status = 'transplanted')""",
    ),
    (
        "every transplanted recipient's waitlist entry is 'fulfilled'",
        """SELECT t.transplant_id FROM transplant t JOIN organ o ON o.organ_id = t.organ_id
         WHERE NOT EXISTS (SELECT 1 FROM waitlist w
                            WHERE w.recipient_id = t.recipient_id
                              AND w.organ_type_id = o.organ_type_id
                              AND w.status = 'fulfilled')""",
    ),
    (
        "no organ comes from a donor whose consent is still 'pending'",
        """SELECT o.organ_id FROM organ o JOIN donor d ON d.patient_id = o.donor_id
         WHERE d.consent_status = 'pending'""",
    ),
    (
        "no living donor gives an organ type that forbids living donation",
        """SELECT o.organ_id FROM organ o
          JOIN donor d ON d.patient_id = o.donor_id
          JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
         WHERE d.donor_type = 'living' AND NOT ot.living_donation_allowed""",
    ),
    (
        "no recipient has two active waitlist rows for the same organ type",
        """SELECT recipient_id FROM waitlist WHERE status = 'active'
         GROUP BY recipient_id, organ_type_id HAVING count(*) > 1""",
    ),
    (
        "no recovery checkup is dated before its transplant",
        """SELECT r.recovery_id FROM recovery r JOIN transplant t ON t.transplant_id = r.transplant_id
         WHERE r.checkup_date < (t.transplant_date AT TIME ZONE 'Asia/Kolkata')::date""",
    ),
    (
        "deceased-type donors are never marked alive",
        "SELECT patient_id FROM donor WHERE donor_type = 'deceased' AND alive_status = 'alive'",
    ),
    (
        "no patient is a minor-aged placeholder (dob not in the future)",
        "SELECT patient_id FROM patient WHERE dob > CURRENT_DATE",
    ),
]

WARNINGS = [  # time-driven conditions: not corruption, but need attention
    (
        "perishable organs still 'available/allocated' past their viability (run expire_organs())",
        """SELECT o.organ_id FROM organ o JOIN organ_type ot ON ot.organ_type_id = o.organ_type_id
         WHERE o.status IN ('available','allocated') AND ot.viability_hours IS NOT NULL
           AND o.harvest_datetime + make_interval(hours => ot.viability_hours) < now()""",
    ),
]


def check_invariants(cur, rep):
    rep.section("DATA INVARIANTS (your real data, read-only)")
    for name, sql in INVARIANTS:
        cur.execute(sql)
        bad = cur.fetchall()
        rep.add(
            "FAIL" if bad else "PASS",
            name,
            f"{len(bad)} violating row(s), first ids: "
            + ", ".join(str(b[0]) for b in bad[:5]),
        )
    for name, sql in WARNINGS:
        cur.execute(sql)
        bad = cur.fetchall()
        rep.add(
            "WARN" if bad else "PASS",
            name,
            f"{len(bad)} organ(s): " + ", ".join(str(b[0]) for b in bad[:5]),
        )


# ---------------------------------------------------------------------------
# 3. rule tests (own fixtures, inside a transaction that is rolled back)
# ---------------------------------------------------------------------------
TX_SQL = (
    "INSERT INTO transplant(organ_id, recipient_id, hosp_id, lead_doctor_id, transplant_date) "
    "VALUES (%s, %s, %s, %s, now() + (%s * interval '1 hour'))"
)


def _one(cur, sql, args=()):
    cur.execute(sql, args)
    return cur.fetchone()[0]


def _expect_error(cur, rep, label, sql, args=(), contains=()):
    """The statement MUST fail, and fail for the right reason (message contains one of `contains`)."""
    cur.execute("SAVEPOINT sp")
    try:
        cur.execute(sql, args)
    except psycopg2.Error as exc:
        cur.execute("ROLLBACK TO SAVEPOINT sp")
        msg = exc.diag.message_primary or str(exc)
        if contains and not any(c.lower() in msg.lower() for c in contains):
            rep.add("FAIL", label, f"rejected for the wrong reason: {msg}")
        else:
            rep.add("PASS", label, msg)
        return
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    rep.add("FAIL", label, "statement was ACCEPTED but should have been rejected")


def _expect_ok(cur, rep, label, fn):
    cur.execute("SAVEPOINT sp")
    try:
        result = fn()
        cur.execute("RELEASE SAVEPOINT sp")
        rep.add(
            "PASS" if result in (None, True) else "FAIL",
            label,
            "" if result in (None, True) else str(result),
        )
    except psycopg2.Error as exc:
        cur.execute("ROLLBACK TO SAVEPOINT sp")
        rep.add("FAIL", label, exc.diag.message_primary or str(exc))


def run_rule_tests(conn, rep):
    rep.section("RULE TESTS (throw-away fixtures, rolled back)")
    cur = conn.cursor()
    tag = uuid.uuid4().hex[:6]

    # ---- fixtures -------------------------------------------------------
    cur.execute(
        "INSERT INTO pincode_area VALUES ('600001','Chennai','Tamil Nadu') ON CONFLICT DO NOTHING"
    )
    hosp = lambda kind: _one(
        cur,
        "INSERT INTO hospital(reg_id,name,facility_type,pincode) "
        "VALUES (%s,%s,%s,'600001') RETURNING hosp_id",
        (f"T-{kind[:2].upper()}-{tag}", f"Test {kind}", kind),
    )
    tc, gen = hosp("transplant_centre"), hosp("general")
    doc = lambda n: _one(
        cur,
        "INSERT INTO doctor(med_bar_id,general_id,name) VALUES (%s,%s,%s) RETURNING doctor_id",
        (f"MB-{n}-{tag}", f"GD-{n}-{tag}", f"Dr Test {n}"),
    )
    d_ok, d_other = doc("ok"), doc("other")
    cur.execute(
        "INSERT INTO doctor_hospital VALUES (%s,%s,'Surgeon',CURRENT_DATE)", (d_ok, tc)
    )

    def patient(name, bg):
        return _one(
            cur,
            "INSERT INTO patient(name,dob,gender,blood_group,hosp_id) "
            "VALUES (%s,'1985-01-01','M',%s,%s) RETURNING patient_id",
            (name, bg, tc),
        )

    def donor(name, bg, dtype, alive, consent):
        pid = patient(name, bg)
        cur.execute(
            "INSERT INTO donor VALUES (%s,%s,%s,%s,NULL)", (pid, dtype, alive, consent)
        )
        return pid

    def recipient(name, bg):
        pid = patient(name, bg)
        cur.execute("INSERT INTO recipient VALUES (%s,2,NULL)", (pid,))
        return pid

    otype = lambda name, hours, living: _one(
        cur,
        "INSERT INTO organ_type(organ_name,viability_hours,living_donation_allowed) "
        "VALUES (%s,%s,%s) RETURNING organ_type_id",
        (f"{name}-{tag}", hours, living),
    )
    t_perish, t_nolive, t_store = (
        otype("perish", 12, True),
        otype("nolive", 4, False),
        otype("store", None, False),
    )

    organ = lambda t, d, hrs_ago=1: _one(
        cur,
        "INSERT INTO organ(organ_type_id,donor_id,full_or_part,harvest_datetime) "
        "VALUES (%s,%s,'full', now() - (%s * interval '1 hour')) RETURNING organ_id",
        (t, d, hrs_ago),
    )
    wait = lambda r, t, h=tc: _one(
        cur,
        "INSERT INTO waitlist(recipient_id,organ_type_id,hosp_id,priority) "
        "VALUES (%s,%s,%s,2) RETURNING waitlist_id",
        (r, t, h),
    )
    status = lambda table, col, pk: _one(
        cur, f"SELECT status FROM {table} WHERE {col}=%s", (pk,)
    )

    donor_ab = donor("Fx Donor AB+", "AB+", "deceased", "deceased", "given")
    donor_liv = donor("Fx Donor A+ living", "A+", "living", "alive", "given")
    donor_pend = donor("Fx Donor pending", "O+", "living", "alive", "pending")
    rec_a, rec_ab, rec_nw = (
        recipient("Fx Rec A+", "A+"),
        recipient("Fx Rec AB+", "AB+"),
        recipient("Fx Rec none", "AB+"),
    )
    wait(rec_a, t_perish)
    wait(rec_ab, t_perish)

    # ---- declarative constraints --------------------------------------
    E = lambda label, sql, args=(), contains=(): _expect_error(
        cur, rep, label, sql, args, contains
    )
    E(
        "invalid blood group rejected",
        "INSERT INTO patient(name,dob,gender,blood_group,hosp_id) VALUES ('x','1990-01-01','M','Z+',%s)",
        (tc,),
        ("check constraint",),
    )
    E(
        "date of birth in the future rejected",
        "INSERT INTO patient(name,dob,gender,blood_group,hosp_id) VALUES ('x','2999-01-01','M','A+',%s)",
        (tc,),
        ("check constraint",),
    )
    E(
        "malformed phone number rejected",
        "INSERT INTO doctor(med_bar_id,general_id,name,contact) VALUES (%s,%s,'x','123')",
        (f"BAD-{tag}", f"BADG-{tag}"),
        ("check constraint",),
    )
    E(
        "duplicate medical-bar id rejected",
        "INSERT INTO doctor(med_bar_id,general_id,name) VALUES (%s,%s,'x')",
        (f"MB-ok-{tag}", f"NEW-{tag}"),
        ("unique",),
    )
    E(
        "waitlist priority outside 1-5 rejected",
        "INSERT INTO waitlist(recipient_id,organ_type_id,hosp_id,priority) VALUES (%s,%s,%s,9)",
        (rec_nw, t_perish, tc),
        ("check constraint",),
    )
    E(
        "recipient cannot be actively waitlisted twice for one organ type",
        "INSERT INTO waitlist(recipient_id,organ_type_id,hosp_id,priority) VALUES (%s,%s,%s,2)",
        (rec_ab, t_perish, tc),
        ("unique",),
    )
    cur.execute("SAVEPOINT p")
    pid = patient("Fx deceased-alive", "A+")
    E(
        "deceased-type donor marked alive rejected",
        "INSERT INTO donor VALUES (%s,'deceased','alive','given',NULL)",
        (pid,),
        ("check constraint",),
    )
    cur.execute("RELEASE SAVEPOINT p")
    E(
        "hospital with staff cannot be deleted (RESTRICT)",
        "DELETE FROM hospital WHERE hosp_id = %s",
        (tc,),
        ("foreign key",),
    )

    # ---- organ rules ---------------------------------------------------
    E(
        "C7  living donor cannot give an organ that forbids living donation",
        "INSERT INTO organ(organ_type_id,donor_id,full_or_part,harvest_datetime) VALUES (%s,%s,'full',now())",
        (t_nolive, donor_liv),
        ("C7",),
    )
    E(
        "C8  donor without consent cannot give an organ",
        "INSERT INTO organ(organ_type_id,donor_id,full_or_part,harvest_datetime) VALUES (%s,%s,'full',now())",
        (t_perish, donor_pend),
        ("C8",),
    )

    # ---- transplant rules ---------------------------------------------
    o = organ(t_perish, donor_ab)
    E(
        "C1  blood-group mismatch (AB+ organ -> A+ recipient)",
        TX_SQL,
        (o, rec_a, tc, d_ok, 0),
        ("C1",),
    )
    E(
        "C2  recipient not waitlisted for that organ type",
        TX_SQL,
        (o, rec_nw, tc, d_ok, 0),
        ("C2",),
    )
    E(
        "C6  hospital is not a transplant centre",
        TX_SQL,
        (o, rec_ab, gen, d_ok, 0),
        ("C6",),
    )
    E(
        "lead doctor must work at the operating hospital",
        TX_SQL,
        (o, rec_ab, tc, d_other, 0),
        ("foreign key",),
    )
    E(
        "C10 transplant before organ harvest",
        TX_SQL,
        (o, rec_ab, tc, d_ok, -3),
        ("C10",),
    )
    o_old = organ(t_perish, donor_ab, 13)
    E(
        "C4  organ past its 12 h viability window",
        TX_SQL,
        (o_old, rec_ab, tc, d_ok, 0),
        ("C4",),
    )
    self_ab = donor("Fx Self AB+", "AB+", "living", "alive", "given")
    cur.execute("INSERT INTO recipient VALUES (%s,2,NULL)", (self_ab,))
    wait(self_ab, t_perish)
    o_self = organ(t_perish, self_ab)
    E(
        "C5  donor cannot receive their own organ",
        TX_SQL,
        (o_self, self_ab, tc, d_ok, 0),
        ("C5",),
    )

    # ---- positive path + status propagation (C9) -----------------------
    def good_transplant():
        cur.execute(TX_SQL, (o, rec_ab, tc, d_ok, 0))
        s_o, s_w = (
            status("organ", "organ_id", o),
            _one(
                cur,
                "SELECT status FROM waitlist WHERE recipient_id=%s AND organ_type_id=%s",
                (rec_ab, t_perish),
            ),
        )
        return (
            True
            if (s_o, s_w) == ("transplanted", "fulfilled")
            else f"organ={s_o}, waitlist={s_w}"
        )

    _expect_ok(
        cur,
        rep,
        "C9  valid transplant succeeds, organ -> 'transplanted', waitlist -> 'fulfilled'",
        good_transplant,
    )
    E(
        "C3  organ already transplanted cannot be transplanted again",
        TX_SQL,
        (o, rec_nw, tc, d_ok, 0),
        ("C3",),
    )
    tx_id = _one(cur, "SELECT transplant_id FROM transplant WHERE organ_id=%s", (o,))
    E(
        "C10 recovery checkup before the transplant date rejected",
        "INSERT INTO recovery(transplant_id,doctor_id,checkup_date,status) VALUES (%s,%s,CURRENT_DATE - 3,'stable')",
        (tx_id, d_ok),
        ("C10",),
    )
    _expect_ok(
        cur,
        rep,
        "valid recovery checkup accepted",
        lambda: cur.execute(
            "INSERT INTO recovery(transplant_id,doctor_id,checkup_date,status) VALUES (%s,%s,CURRENT_DATE,'stable')",
            (tx_id, d_ok),
        ),
    )

    # ---- donor guards --------------------------------------------------
    E(
        "C12 deceased donor cannot be marked alive again",
        "UPDATE donor SET alive_status='alive' WHERE patient_id=%s",
        (donor_ab,),
        ("C12",),
    )
    o_liv = organ(t_perish, donor_liv)
    cur.execute(TX_SQL, (o_liv, rec_a, tc, d_ok, 0))
    E(
        "C13 consent cannot be withdrawn after the organ is transplanted",
        "UPDATE donor SET consent_status='withdrawn' WHERE patient_id=%s",
        (donor_liv,),
        ("C13",),
    )

    # ---- helper functions ----------------------------------------------
    o_m = organ(t_perish, donor_ab)
    wait(rec_ab, t_perish)  # earlier entry is 'fulfilled'; this is a new active one
    wait(rec_nw, t_nolive)  # different organ type, must NOT appear
    cur.execute("SELECT recipient_id FROM find_matches(%s)", (o_m,))
    got = {r[0] for r in cur.fetchall()}
    rep.add(
        "PASS"
        if (rec_ab in got and rec_a not in got and rec_nw not in got)
        else "FAIL",
        "find_matches() returns compatible, same-type waitlisted recipients only",
        f"got ids {sorted(got)}",
    )

    o_exp = organ(t_perish, donor_ab, 20)  # 20 h old, 12 h window
    o_keep = organ(t_store, donor_ab, 500)  # storable organ never expires
    cur.execute("SELECT expire_organs()")
    s_exp, s_keep = (
        status("organ", "organ_id", o_exp),
        status("organ", "organ_id", o_keep),
    )
    rep.add(
        "PASS" if (s_exp, s_keep) == ("expired", "available") else "FAIL",
        "expire_organs() expires perishable organs only",
        f"perishable={s_exp}, storable={s_keep}",
    )

    cur.close()


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def run_all_checks(
    conn=None,
    expect_seed=False,
    include_invariants=True,
    include_rule_tests=True,
    verbose=True,
) -> bool:
    """Run everything. Returns True when nothing failed. Never changes your data."""
    own = conn is None
    conn = conn or get_connection()
    rep = Report(verbose)
    try:
        was_auto = conn.autocommit
        conn.autocommit = False
        with conn.cursor() as cur:
            check_schema(cur, rep)
            if expect_seed:
                check_seed_counts(cur, rep)
            if include_invariants and not rep.failed:
                check_invariants(cur, rep)
        conn.rollback()
        if include_rule_tests and not rep.failed:
            try:
                run_rule_tests(conn, rep)
            finally:
                conn.rollback()  # nothing from the tests is ever kept
        conn.autocommit = was_auto
    finally:
        if own:
            conn.close()
    return rep.summary()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--seed", action="store_true", help="also verify the mock-data row counts"
    )
    sys.exit(0 if run_all_checks(expect_seed=ap.parse_args().seed) else 1)
