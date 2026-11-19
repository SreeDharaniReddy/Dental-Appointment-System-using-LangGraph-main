# Dental Appointment System — LangGraph + Claude + PostgreSQL

An AI assistant for a dental clinic's front desk. Staff type requests in plain English
(*"Book patient 1000082 with Kevin Anderson on 2/9/2026 8:30"*) and the assistant
checks, books, cancels and reschedules appointments in a **PostgreSQL** database.

Based on [pik1989/Dental-Appointment-System-using-LangGraph](https://github.com/pik1989/Dental-Appointment-System-using-LangGraph),
which used Grok-4 and stored data in a CSV file.

## What I changed from the original
| Original | This version |
|---|---|
| Data in a CSV file (pandas) | Data in **PostgreSQL**; edit it live in pgAdmin while the assistant runs |
| Grok-4 (xAI) | **Claude** (Anthropic) via `langchain-anthropic` |
| API key typed into `settings.py` | Secrets kept in a `.env` file (not committed) |
| Whole file re-written on every change | Single-row `UPDATE`s inside **transactions** |
| Two bookings for the same slot could both succeed | `WHERE is_available = TRUE` ensures only one wins |
| A patient could be booked with two doctors at once | Booking and rescheduling refuse a patient's time clash |
| No database rules | `UNIQUE` and `CHECK` constraints reject invalid rows |

## How it works
```
You type a request → main.py → LangGraph agent (Claude)
                                   ↓ chooses a tool
                       dental_agent/tools/*.py → PostgreSQL
```
Claude reads the request, calls one of 7 tools (find free slots, check a slot, list doctors,
look up a patient, book, cancel, reschedule), reads the result, and replies.

## Project structure
```
main.py                        # Interactive terminal chat
dental_agent/
  agent.py                     # Claude + tools + system prompt (LangGraph agent)
  db.py                        # PostgreSQL connection (settings from .env)
  config/settings.py           # Model name, API key from .env
  tools/csv_reader.py          # Read tools  (SQL SELECTs)
  tools/csv_writer.py          # Write tools (SQL UPDATEs in transactions)
SQL/schema.sql                 # Creates the appointments table
doctor_availability.csv        # Sample data (4,280 slots) to import
test_tools.py                  # Tests every tool without the AI
```

## Setup
1. **Install PostgreSQL** (pgAdmin included) and create a database named `dental_db`.
2. In pgAdmin → `dental_db` → **Query Tool**, run `SQL/schema.sql`.
3. **Import the data:** right-click the `appointments` table → *Import/Export Data* →
   choose `doctor_availability.csv`, format **csv**, **Header on**, and remove `id` from the columns.
4. **Python environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. **Create a `.env` file** next to `main.py`:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=dental_db
   DB_USER=postgres
   DB_PASSWORD=your_postgres_password
   ANTHROPIC_API_KEY=your_anthropic_api_key
   MODEL_NAME=claude-opus-5-5
   ```
6. **Test the database tools** (no AI needed):
   ```bash
   python test_tools.py
   ```
7. **Run the assistant:**
   ```bash
   python main.py
   ```

## Example requests
- `Show available slots for an orthodontist`
- `Book patient 1000082 with Kevin Anderson on 2/9/2026 8:30`
- `What appointments does patient 1000082 have?`
- `Reschedule patient 1000082 from 2/9/2026 8:30 to 2/9/2026 9:00 with Kevin Anderson`
- `Cancel the appointment for patient 1000082 at 2/9/2026 9:00`

## Tech stack
LangGraph · LangChain · Claude (Anthropic) · PostgreSQL · psycopg 3 · python-dotenv
