from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from dental_agent.config.settings import ANTHROPIC_API_KEY, MODEL_NAME
from dental_agent.tools.csv_reader import (
    get_available_slots,
    get_patient_appointments,
    check_slot_availability,
    list_doctors_by_specialization,
)
from dental_agent.tools.csv_writer import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
)

TOOLS = [
    get_available_slots,
    get_patient_appointments,
    check_slot_availability,
    list_doctors_by_specialization,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
]

SYSTEM_PROMPT = """You are a helpful dental appointment assistant. You help patients with:

1. Checking available appointment slots and doctor information
2. Booking new appointments
3. Cancelling existing appointments
4. Rescheduling appointments

## Available Specializations
general_dentist, oral_surgeon, orthodontist, cosmetic_dentist,
prosthodontist, pediatric_dentist, emergency_dentist

## Date Format
Always use M/D/YYYY H:MM format — e.g. 5/10/2026 9:00

## Booking Rules
- Always call check_slot_availability before booking to confirm the slot is free
- If a slot is taken, call get_available_slots to suggest alternatives
- Always confirm cancellations before executing them
- Ask for one missing detail at a time — don't overwhelm the user

## Formatting
Your replies are shown in a plain-text terminal. Do not use Markdown (no **bold**, no # headings, no tables). Use simple lines and dashes for lists.
"""

# The "brain": Claude, via LangChain.
llm = ChatAnthropic(
    model=MODEL_NAME,
    api_key=ANTHROPIC_API_KEY,
    max_tokens=16000,
    # If Claude declines a request for safety reasons, the API automatically
    # retries it on a fallback model instead of just stopping.
    betas=["server-side-fallback-2026-07-01"],
    model_kwargs={"fallbacks": "default"},
)

# The agent: Claude + our database tools, in a LangGraph loop
# (think -> call a tool -> read the result -> think again -> answer).
dental_graph = create_react_agent(model=llm, tools=TOOLS, prompt=SYSTEM_PROMPT)