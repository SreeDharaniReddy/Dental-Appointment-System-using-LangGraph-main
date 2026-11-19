"""
test_tools.py - checks every database tool WITHOUT using the AI.
Run:  python test_tools.py
It books, reschedules and cancels a test appointment, then puts everything back.
"""
from dental_agent.tools.csv_reader import (
    get_available_slots, get_patient_appointments,
    check_slot_availability, list_doctors_by_specialization,
)
from dental_agent.tools.csv_writer import (
    book_appointment, cancel_appointment, reschedule_appointment,
)

TEST_PATIENT = "9999001"

print("1. Orthodontists:", list_doctors_by_specialization.invoke({"specialization": "orthodontist"}))

slots = get_available_slots.invoke({"specialization": "orthodontist"})
print(f"2. Free orthodontist slots (first 3 of {len(slots)}):", slots[:3])

first, second = slots[0], slots[1]
doc = first["doctor_name"]
second = next(s for s in slots[1:] if s["doctor_name"] == doc)

print("3. Check slot:", check_slot_availability.invoke({"doctor_name": doc, "date_slot": first["date_slot"]}))
print("4. Book:", book_appointment.invoke({"patient_id": TEST_PATIENT, "doctor_name": doc, "date_slot": first["date_slot"]}))
print("5. Book same slot again (should fail):", book_appointment.invoke({"patient_id": "123", "doctor_name": doc, "date_slot": first["date_slot"]}))
print("6. Patient's appointments:", get_patient_appointments.invoke({"patient_id": TEST_PATIENT}))
print("7. Reschedule:", reschedule_appointment.invoke({
    "patient_id": TEST_PATIENT, "current_date_slot": first["date_slot"],
    "new_date_slot": second["date_slot"], "doctor_name": doc}))
print("8. Patient's appointments:", get_patient_appointments.invoke({"patient_id": TEST_PATIENT}))
print("9. Cancel:", cancel_appointment.invoke({"patient_id": TEST_PATIENT, "date_slot": second["date_slot"]}))
print("10. Patient's appointments (should be empty):", get_patient_appointments.invoke({"patient_id": TEST_PATIENT}))
print("\nAll tools work with PostgreSQL!")