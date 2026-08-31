from dotenv import load_dotenv
load_dotenv()
from app.db import init_db
from app.agent_runner import run_pipeline

if __name__ == "__main__":
    init_db()
    run_pipeline()