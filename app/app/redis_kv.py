import os, redis
r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

def acquire_once(key: str, ttl_sec: int = 3600) -> bool:
    # Idempotencia: SET if Not eXists + expiración
    return r.set(name=key, value="1", nx=True, ex=ttl_sec) is True