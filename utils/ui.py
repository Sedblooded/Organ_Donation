from typing import Callable, List, Dict, Any, Optional
import psycopg2
import streamlit as st
import db_conn


def init_session_state():
    """Ensure baseline session state keys exist."""
    if "role" not in st.session_state:
        st.session_state["role"] = "Admin"
    if "hospital_id" not in st.session_state:
        st.session_state["hospital_id"] = None
    if "hospital_name" not in st.session_state:
        st.session_state["hospital_name"] = "All Hospitals"
    if "selected_organ_id" not in st.session_state:
        st.session_state["selected_organ_id"] = None
    if "selected_recipient_id" not in st.session_state:
        st.session_state["selected_recipient_id"] = None
    if "selected_waitlist_id" not in st.session_state:
        st.session_state["selected_waitlist_id"] = None


def require_role(allowed_roles: List[str]):
    """Gate access to a page based on selected role."""
    init_session_state()
    user_role = st.session_state.get("role", "Admin")
    if user_role not in allowed_roles:
        st.warning(f"Access restricted. This page requires one of: **{', '.join(allowed_roles)}** (Current role: **{user_role}**).")
        st.stop()


def render_sidebar():
    """Render the standard app sidebar across all pages."""
    init_session_state()
    with st.sidebar:
        st.markdown("### Organ Donation Portal")
        st.caption("Organ & Tissue Transplant Network")

        st.divider()

        # Role selector
        roles = ["Admin", "Doctor", "Hospital Staff"]
        current_role_idx = roles.index(st.session_state["role"]) if st.session_state["role"] in roles else 0
        new_role = st.selectbox("Select Your Role", roles, index=current_role_idx, key="_sidebar_role_select")
        if new_role != st.session_state["role"]:
            st.session_state["role"] = new_role
            st.rerun()

        # Hospital selector (if Doctor or Hospital Staff)
        if st.session_state["role"] in ["Doctor", "Hospital Staff"]:
            try:
                hospitals = db_conn.fetch_all("SELECT hosp_id, name, facility_type FROM hospital ORDER BY name;")
                hosp_options = [{"hosp_id": None, "name": "All Hospitals", "facility_type": ""}] + hospitals
                hosp_names = [h["name"] for h in hosp_options]

                # Match existing selection
                current_hosp_id = st.session_state.get("hospital_id")
                match_idx = 0
                for idx, h in enumerate(hosp_options):
                    if h["hosp_id"] == current_hosp_id:
                        match_idx = idx
                        break

                selected_idx = st.selectbox(
                    "Affiliated Hospital",
                    range(len(hosp_options)),
                    format_func=lambda i: hosp_names[i],
                    index=match_idx,
                    key="_sidebar_hosp_select"
                )
                selected_h = hosp_options[selected_idx]
                if selected_h["hosp_id"] != st.session_state.get("hospital_id"):
                    st.session_state["hospital_id"] = selected_h["hosp_id"]
                    st.session_state["hospital_name"] = selected_h["name"]
                    st.rerun()
            except Exception as e:
                st.caption(f"Unable to load hospitals: {e}")
        else:
            st.session_state["hospital_id"] = None
            st.session_state["hospital_name"] = "All Hospitals"

        st.divider()

        # DB connection indicator
        is_alive = db_conn.check_connection()
        if is_alive:
            st.success("Database Connected")
        else:
            st.error("Database Disconnected")


def select_from_rows(
    label: str,
    rows: List[Dict[str, Any]],
    id_key: str,
    label_fn: Callable[[Dict[str, Any]], str],
    key: Optional[str] = None,
    empty_label: Optional[str] = None,
    default_id: Optional[Any] = None
) -> Optional[Any]:
    """Helper for selectboxes that display formatted labels but return primary IDs."""
    if not rows and not empty_label:
        st.info(f"No {label.lower()} available.")
        return None

    options = []
    if empty_label is not None:
        options.append({"_id": None, "_label": empty_label})

    for r in rows:
        options.append({"_id": r[id_key], "_label": label_fn(r)})

    default_idx = 0
    if default_id is not None:
        for idx, opt in enumerate(options):
            if opt["_id"] == default_id:
                default_idx = idx
                break

    chosen = st.selectbox(
        label,
        options,
        index=default_idx,
        format_func=lambda opt: opt["_label"],
        key=key
    )
    return chosen["_id"] if chosen else None


def show_success(msg: str):
    """Render a clean success alert."""
    st.success(msg)


def show_db_error(exc: Exception):
    """Translate Postgres / Python exceptions to human-friendly feedback."""
    err_str = str(exc)
    if "unique constraint" in err_str.lower():
        st.error("Duplicate Record: A record with that identifier or unique attribute already exists.")
    elif "foreign key constraint" in err_str.lower():
        st.error("Reference Error: This record references missing data or cannot be removed because it is in use.")
    elif "check constraint" in err_str.lower():
        st.error("Validation Error: One or more fields violate business rules (check constraints).")
    elif "C1:" in err_str:
        st.error("Blood Compatibility Violation: The donor's blood group cannot donate to the recipient.")
    elif "C2:" in err_str:
        st.error("Waitlist Violation: Recipient is not actively listed for this organ type.")
    elif "C3:" in err_str:
        st.error("Availability Violation: Organ is already allocated, transplanted, or unavailable.")
    elif "C4:" in err_str:
        st.error("Viability Window Expired: The organ has passed its maximum viable hours.")
    elif "C5:" in err_str:
        st.error("Invalid Match: Donor and recipient cannot be the same patient.")
    elif "C6:" in err_str:
        st.error("Hospital Facility Error: Transplants can only occur at registered transplant centres.")
    elif "C7:" in err_str:
        st.error("Living Donor Restriction: Living donors cannot donate this organ type.")
    elif "C8:" in err_str:
        st.error("Consent Missing: Donor consent is not 'given'.")
    elif "C10:" in err_str:
        st.error("Date Sequence Error: Event date occurs before prerequisites.")
    elif "C12:" in err_str:
        st.error("Status Error: A deceased donor cannot be marked alive.")
    elif "C13:" in err_str:
        st.error("Irrevocable Consent: Consent cannot be withdrawn after an organ is transplanted.")
    else:
        st.error(f"Operation failed: {err_str}")


def time_remaining_badge(hours: Optional[float], is_expired: bool) -> str:
    """Return badge for time remaining."""
    if hours is None:
        return "Storable"
    if is_expired:
        return f"Expired ({abs(hours):.1f}h ago)"
    if hours < 4:
        return f"Critical ({hours:.1f}h left)"
    if hours <= 12:
        return f"Urgent ({hours:.1f}h left)"
    return f"{hours:.1f}h left"
