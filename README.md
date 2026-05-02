# retirement-planning-v2

Phase 1 project shell for Retirement Planning V2.

## Backend
- Minimal FastAPI app with `/health`

### Run
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Test
```bash
python -m pytest -q
```

## Frontend
- React + TypeScript placeholder routes

### Run
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### Test
```bash
npm run test
```

## Notes
- No business logic
- No DB schema
- No V1 code copied
