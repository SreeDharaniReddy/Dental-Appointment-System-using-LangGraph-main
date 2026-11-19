CREATE TABLE appointments (
    id                SERIAL PRIMARY KEY,
    date_slot         TIMESTAMP    NOT NULL,
    specialization    VARCHAR(50)  NOT NULL,
    doctor_name       VARCHAR(100) NOT NULL,
    is_available      BOOLEAN      NOT NULL DEFAULT TRUE,
    patient_to_attend VARCHAR(20),

    CONSTRAINT one_slot_per_doctor UNIQUE (doctor_name, date_slot),
    CONSTRAINT booked_needs_patient CHECK (
        (is_available = TRUE  AND patient_to_attend IS NULL) OR
        (is_available = FALSE AND patient_to_attend IS NOT NULL)
    )
);