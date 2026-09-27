import sys
sys.path.insert(0, 'backend')
import asyncio
import json
from backend.modules.pipeline import run
from backend.db import get_db, init_db

async def main():
    await init_db('mongodb://localhost:27017', 'sanskrit_nlp_test')
    db = get_db()
    res = await run(db, 'boy, play')
    with open('test_output.json', 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

asyncio.run(main())
