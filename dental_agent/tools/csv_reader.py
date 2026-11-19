"""
csv_reader.py - READ tools (the assistant uses these to look things up).

Same tool names, inputs and outputs as the original project,
but the data now comes from PostgreSQL instead of the CSV file.
"""

from datetime import datetime

from langchain_core.tools import tool

from dental_agent.db import get_connection

# Date formats we accept from the user / the AI, e.g. "5/10/2026 9:00"
_DATE_FORMATS = ["%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]


def parse_date_slot(text: str) -> datetime:
    """Turn '5/10/2026 9:00' (or '2026-05-10 09:00') into a datetime. Raises ValueError if invalid."""
    text = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"Invalid date_slot: {text}")


def format_date_slot(dt: datetime) -> str:
    """Turn a datetime into '5/10/2026 9:00' (the format the original project used)."""
    return f"{dt.month}/{dt.day}/{dt.year} {dt.hour}:{dt.minute:02d}"


@tool
def get_available_slots(
    specialization: str = "",
    doctor_name: str = "",
    date_filter: str = "",
) -> list:
    """
    Return available (is_available=TRUE) appointment slots.

    Args:
        specialization: Filter by specialization, e.g. 'orthodontist'. Leave empty to skip.
        doctor_name: Filter by doctor name (case-insensitive), e.g. 'emily johnson'. Leave empty to skip.
        date_filter: Filter by date string M/D/YYYY, e.g. '5/10/2026'. Leave empty to skip.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name.
        Returns at most 20 rows to keep response concise.
    """
    sql = "SELECT date_slot, specialization, doctor_name FROM appointments WHERE is_available = TRUE"
    params = []

    if specialization:
        sql += " AND LOWER(specialization) = %s"
        params.append(specialization.lower().strip())
    if doctor_name:
        sql += " AND LOWER(doctor_name) = %s"
        params.append(doctor_name.lower().strip())
    if date_filter:
        try:
            day = datetime.strptime(date_filter.strip(), "%m/%d/%Y").date()
            sql += " AND date_slot::date = %s"
            params.append(day)
        except ValueError:
            pass  # same as the original: ignore a bad date filter

    sql += " ORDER BY date_slot LIMIT 20"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        {
            "date_slot": format_date_slot(r["date_slot"]),
            "specialization": r["specialization"],
            "doctor_name": r["doctor_name"],
        }
        for r in rows
    ]


@tool
def get_patient_appointments(patient_id: str) -> list:
    """
    Return all booked appointments for a given patient ID.

    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name, patient_to_attend.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT date_slot, specialization, doctor_name, patient_to_attend
            FROM appointments
            WHERE patient_to_attend = %s
            ORDER BY date_slot
            """,
            [str(patient_id).strip()],
        ).fetchall()

    return [{**r, "date_slot": format_date_slot(r["date_slot"])} for r in rows]


@tool
def check_slot_availability(doctor_name: str, date_slot: str) -> dict:
    """
    Check if a specific doctor slot is available.

    Args:
        doctor_name: Doctor name, e.g. 'emily johnson'.
        date_slot: Slot string in M/D/YYYY H:MM format, e.g. '5/10/2026 9:00'.

    Returns:
        Dict with keys: found (bool), is_available (bool), patient_to_attend (str).
    """
    try:
        target = parse_date_slot(date_slot)
    except ValueError:
        return {"found": False, "is_available": False, "patient_to_attend": ""}

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT is_available, patient_to_attend
            FROM appointments
            WHERE LOWER(doctor_name) = %s AND date_slot = %s
            """,
            [doctor_name.lower().strip(), target],
        ).fetchone()

    if row is None:
        return {"found": False, "is_available": False, "patient_to_attend": ""}

    return {
        "found": True,
        "is_available": row["is_available"],
        "patient_to_attend": row["patient_to_attend"] or "",
    }


@tool
def list_doctors_by_specialization(specialization: str) -> list:
    """
    Return distinct doctor names for a given specialization.

    Args:
        specialization: e.g. 'orthodontist'.

    Returns:
        Sorted list of doctor name strings.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT doctor_name
            FROM appointments
            WHERE LOWER(specialization) = %s
            ORDER BY doctor_name
            """,
            [specialization.lower().strip()],
        ).fetchall()

    return [r["doctor_name"] for r in rows]