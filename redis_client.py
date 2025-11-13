
import redis
import os

# You can also put this in your .env file
REDIS_URL = "rediss://default:OLde0zTPDsSiNutDocUtjwVnlMq6yfgP@redis-12043.c279.us-central1-1.gce.redns.redis-cloud.com:12043"

# Create Redis client
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Test
r.set("foo", "bar")
print(r.get("foo"))  # Should print 'bar'