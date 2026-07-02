#!/bin/bash
# ──────────────────────────────────────────────────────────────
# MeetSmart AI — One-command startup script
# Starts both FastAPI backend and React frontend
# ──────────────────────────────────────────────────────────────

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "🧠  MeetSmart AI — ThinkPalm Internal Meeting Platform"
echo "════════════════════════════════════════════════════════"

# Check .env exists
if [ ! -f ".env" ]; then
  echo "⚠️  .env not found — copying from .env.example"
  cp .env.example .env
  echo "✅ Created .env (edit it to add Gemini API key or Gmail credentials)"
fi

# Create outputs dir
mkdir -p outputs samples

# Seed database
echo ""
echo "⚙️  Seeding database..."
python3 src/db/seed.py

# Generate sample files
echo ""
echo "📁 Generating sample .ics and .docx files..."
python3 - <<'EOF'
import sys
sys.path.insert(0, ".")
from src.services.ics_service import build_sample_ics
from src.services.docx_service import build_sample_mom
ics = build_sample_ics()
print(f"  ✅ Sample .ics → {ics}")
mom = build_sample_mom()
print(f"  ✅ Sample .docx → {mom}")
EOF

# Start backend (background)
echo ""
echo "🚀 Starting FastAPI backend on http://localhost:8000 ..."
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend
sleep 2

# Start frontend
echo ""
echo "⚡ Starting React frontend on http://localhost:5173 ..."
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!

cd "$PROJECT_DIR"

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ MeetSmart AI is running!"
echo ""
echo "   🌐 Frontend  →  http://localhost:5173"
echo "   📡 API       →  http://localhost:8000"
echo "   📖 API Docs  →  http://localhost:8000/docs"
echo ""
echo "   Press Ctrl+C to stop all services."
echo "════════════════════════════════════════════════════════"

# Wait for Ctrl+C and cleanup
trap "echo ''; echo '🛑 Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
