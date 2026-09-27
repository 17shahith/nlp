import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
import asyncio
import json
from modules.pipeline import run
from db import get_db, ensure_indexes

async def main():
    await ensure_indexes()
    db = get_db()
    res = await run(db, 'boy, play')
    with open('test_output.json', 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

asyncio.run(main())
