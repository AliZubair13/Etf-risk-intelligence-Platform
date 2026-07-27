# ETF Risk Attribution & Event Intelligence Platform

An analyst-facing platform that answers: **Why did this ETF move unusually on this date?**

## Quick Start

```bash
cp .env.example .env
docker compose up -d
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000
streamlit run streamlit_app/app.py --server.port 3000
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## Disclaimer
Educational tool only. Not investment advice.
