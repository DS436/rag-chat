"""RQ worker entrypoint. Run from the backend/ directory: python worker.py"""

from redis import Redis
from rq import Queue, Worker

from app.core.config import settings

if __name__ == "__main__":
    conn = Redis.from_url(settings.redis_url)
    queue = Queue("ingest", connection=conn)
    worker = Worker([queue], connection=conn)
    worker.work()
