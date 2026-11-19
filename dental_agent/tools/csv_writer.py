"""
csv_writer.py - WRITE tools (book, cancel, reschedule).

Same tool names, inputs and outputs as the original project,
but the changes are now saved in PostgreSQL instead of the CSV file.

Each tool runs inside ONE database transaction ("with get_connection()"):
either every change is saved, or (if anything fails) nothing is.
"""

from langchain_core.tools import tool

from dental_agent.db import get_connection
from dental_agent.tools.csv_reader import parse_date_slot


@tool
def book_appointment(patient_id: str, doctor_name: str, date_slot: str) -> dict:
    """
    Book an appointment: mark slot as unavailable and assign patient_id.

    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.
        doctor_name: Doctor name (case-insensitive), e.g. 'emily johnson'.
        date_slot: Slot in M/D/YYYY H:MM format, e.g. '5/10/2026 9:00'.

    Returns:
        Dict with keys: success (bool), message (str).
    """
    try:
        target = parse_date_slot(date_slot)
    except ValueError:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    doc = doctor_name.lower().strip()
    pid = str(patient_id).strip()

    with get_connection() as conn:
        # A patient can't be in two places at once.
        clash = conn.execute(
            "SELECT doctor_name FROM appointments WHERE patient_to_attend = %s AND date_slot = %s",
            [pid, target],
        ).fetchone()
        if clash is not None:
            return {
                "success": False,
                "message": f"Patient {pid} already has an appointment at {date_slot} with {clash['doctor_name']}.",
            }

        # Only updates the row if it is STILL free -> two people can't book the same slot.
        booked = conn.execute(
            """
            UPDATE appointments
            SET is_available = FALSE, patient_to_attend = %s
            WHERE LOWER(doctor_name) = %s AND date_slot = %s AND is_available = TRUE
            RETURNING id
            """,
            [pid, doc, target],
        ).fetchone()

        if booked is None:
            exists = conn.execute(
                "SELECT 1 FROM appointments WHERE LOWER(doctor_name) = %s AND date_slot = %s",
                [doc, target],
            ).fetchone()
            if exists is None:
                return {"success": False, "message": "Slot not found for this doctor."}
            return {"success": False, "message": "Slot is already booked."}

    return {
        "success": True,
        "message": f"Appointment booked for patient {patient_id} with {doctor_name} at {date_slot}.",
    }


@tool
def cancel_appointment(patient_id: str, date_slot: str) -> dict:
    """
    Cancel an appointment: mark slot available and clear patient_id.

    Args:
        patient_id: Patient whose appointment to cancel.
        date_slot: Slot in M/D/YYYY H:MM format to cancel.

    Returns:
        Dict with keys: success (bool), message (str).
    """
    try:
        target = parse_date_slot(date_slot)
    except ValueError:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    with get_connection() as conn:
        cancelled = conn.execute(
            """
            UPDATE appointments
            SET is_available = TRUE, patient_to_attend = NULL
            WHERE patient_to_attend = %s AND date_slot = %s AND is_available = FALSE
            RETURNING id
            """,
            [str(patient_id).strip(), target],
        ).fetchall()

    if not cancelled:
        return {
            "success": False,
            "message": f"No booked appointment found for patient {patient_id} at {date_slot}.",
        }
    return {
        "success": True,
        "message": f"Appointment at {date_slot} for patient {patient_id} has been cancelled.",
    }


@tool
def reschedule_appointment(
    patient_id: str,
    current_date_slot: str,
    new_date_slot: str,
    doctor_name: str,
) -> dict:
    """
    Reschedule by cancelling the old slot and booking a new one atomically.

    Args:
        patient_id: Patient whose appointment to reschedule.
        current_date_slot: Existing booked slot to vacate (M/D/YYYY H:MM).
        new_date_slot: Desired new slot (M/D/YYYY H:MM).
        doctor_name: Doctor name (must match the booking's doctor).

    Returns:
        Dict with keys: success (bool), message (str).
    """
    try:
        current_dt = parse_date_slot(current_date_slot)
        new_dt = parse_date_slot(new_date_slot)
    except ValueError as exc:
        return {"success": False, "message": f"Date parse error: {exc}"}

    doc = doctor_name.lower().strip()
    pid = str(patient_id).strip()

    with get_connection() as conn:
        # 1. Find the existing booking (FOR UPDATE = lock it while we work)
        old = conn.execute(
            """
            SELECT id FROM appointments
            WHERE patient_to_attend = %s AND date_slot = %s AND is_available = FALSE
            FOR UPDATE
            """,
            [pid, current_dt],
        ).fetchone()
        if old is None:
            return {
                "success": False,
                "message": f"No existing booking found for patient {pid} at {current_date_slot}.",
            }

        # 2. Book the new slot (only if it is still free)
        # 2. A patient can't be in two places at once (ignore the booking we are moving)
        clash = conn.execute(
            """
            SELECT doctor_name FROM appointments
            WHERE patient_to_attend = %s AND date_slot = %s AND id <> %s
            """,
            [pid, new_dt, old["id"]],
        ).fetchone()
        if clash is not None:
            return {
                "success": False,
                "message": f"Patient {pid} already has an appointment at {new_date_slot} with {clash['doctor_name']}.",
            }

        # 3. Book the new slot (only if it is still free)
        new = conn.execute(
            """
            UPDATE appointments
            SET is_available = FALSE, patient_to_attend = %s
            WHERE LOWER(doctor_name) = %s AND date_slot = %s AND is_available = TRUE
            RETURNING id
            """,
            [pid, doc, new_dt],
        ).fetchone()
        if new is None:
            exists = conn.execute(
                "SELECT 1 FROM appointments WHERE LOWER(doctor_name) = %s AND date_slot = %s",
                [doc, new_dt],
            ).fetchone()
            if exists is None:
                return {"success": False, "message": f"Slot {new_date_slot} does not exist for {doctor_name}."}
            return {"success": False, "message": f"Slot {new_date_slot} is already taken."}

        # 3. Free the old slot
        conn.execute(
            "UPDATE appointments SET is_available = TRUE, patient_to_attend = NULL WHERE id = %s",
            [old["id"]],
        )

    return {
        "success": True,
        "message": (
            f"Appointment for patient {pid} rescheduled from "
            f"{current_date_slot} to {new_date_slot} with {doctor_name}."
        ),
    }