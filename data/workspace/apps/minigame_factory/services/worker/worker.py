import os
from redis import Redis
from rq import Worker, Queue, Connection

REDIS_URL = os.environ["REDIS_URL"]
listen = ["build"]
redis_conn = Redis.from_url(REDIS_URL)

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker([Queue(n) for n in listen])
        worker.work()
