# AGIDash

Bayesian early-warning dashboard for an AGI-perception cascade.

## Setup

1. Copy the example environment file and set the variables:
   cp .env.example .env

2. Install dependencies with Poetry:
   poetry install

3. Start services with Docker Compose:
   docker compose up -d

   - Dagster web UI on http://localhost:3000
   - Streamlit dashboard on http://localhost:8501

4. (One-time) From the Dagster web UI, kick off a backfill for the initial run.
