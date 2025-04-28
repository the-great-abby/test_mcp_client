import time
import json

HEALTH_CHECK_PATH = "/health"

class SyncMockRedis:
    def __init__(self):
        self.store = {}
        self.expiry = {}
    def get(self, key):
        return self.store.get(key)
    def set(self, key, value, ex=None):
        self.store[key] = value
        return True
    def delete(self, key):
        self.store.pop(key, None)
        return True
    def pipeline(self):
        return self  # For simplicity, just return self

class MockRedisPipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []
    async def set(self, key, value, ex=None):
        self.commands.append(('set', key, value, ex))
        return self
    async def get(self, key):
        self.commands.append(('get', key))
        return self
    async def delete(self, key):
        self.commands.append(('delete', key))
        return self
    async def hincrby(self, name, key, amount=1):
        self.commands.append(('hincrby', name, key, amount))
        return self
    async def hgetall(self, name):
        self.commands.append(('hgetall', name))
        return self
    async def expire(self, key, ex):
        self.commands.append(('expire', key, ex))
        return self
    async def execute(self):
        results = []
        for cmd in self.commands:
            if cmd[0] == 'set':
                results.append(await self.redis.set(cmd[1], cmd[2], ex=cmd[3]))
            elif cmd[0] == 'get':
                results.append(await self.redis.get(cmd[1]))
            elif cmd[0] == 'delete':
                results.append(await self.redis.delete(cmd[1]))
            elif cmd[0] == 'hincrby':
                results.append(await self.redis.hincrby(cmd[1], cmd[2], cmd[3]))
            elif cmd[0] == 'hgetall':
                results.append(await self.redis.hgetall(cmd[1]))
            elif cmd[0] == 'expire':
                results.append(await self.redis.expire(cmd[1], cmd[2]))
        self.commands = []
        return results

class MockRedis:
    def __init__(self):
        self.store = {}
        self.expiry = {}
        self.hash_store = {}

    async def get(self, key):
        # Handle expiry
        if key in self.expiry and time.time() > self.expiry[key]:
            self.store.pop(key, None)
            self.expiry.pop(key, None)
            return None
        value = self.store.get(key)
        if value is None:
            return None
        # Always return bytes, as real Redis does
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return value.encode("utf-8")
        # For other types, serialize to JSON and encode
        return json.dumps(value).encode("utf-8")

    async def set(self, key, value, ex=None):
        # Store as bytes
        if isinstance(value, str):
            value = value.encode("utf-8")
        elif not isinstance(value, bytes):
            value = json.dumps(value).encode("utf-8")
        self.store[key] = value
        if ex is not None:
            self.expiry[key] = time.time() + ex
        elif key in self.expiry:
            self.expiry.pop(key)
        return True

    async def delete(self, key):
        self.store.pop(key, None)
        self.expiry.pop(key, None)
        self.hash_store.pop(key, None)
        return True

    async def hincrby(self, name, key, amount=1):
        if name not in self.hash_store:
            self.hash_store[name] = {}
        self.hash_store[name][key] = self.hash_store[name].get(key, 0) + amount
        return self.hash_store[name][key]

    async def hgetall(self, name):
        # Return a dict of key: value (as bytes, like real Redis)
        if name not in self.hash_store:
            return {}
        return {k.encode("utf-8"): str(v).encode("utf-8") for k, v in self.hash_store[name].items()}

    async def expire(self, key, ex):
        self.expiry[key] = time.time() + ex
        return True

    async def keys(self, pattern):
        # Only support '*' wildcard at start or end for simplicity
        if pattern == '*':
            return list(self.store.keys())
        if pattern.endswith('*'):
            prefix = pattern[:-1]
            return [k for k in self.store.keys() if k.startswith(prefix)]
        if pattern.startswith('*'):
            suffix = pattern[1:]
            return [k for k in self.store.keys() if k.endswith(suffix)]
        return [k for k in self.store.keys() if k == pattern]

    def pipeline(self):
        return MockRedisPipeline(self)

    async def incr(self, key):
        value = self.store.get(key)
        print(f"[DEBUG][MockRedis.incr] Called with key: {key}, previous value: {value}")
        if value is None:
            self.store[key] = b"1"
            print(f"[DEBUG][MockRedis.incr] Set {key} to 1 (new key)")
            return 1
        try:
            current = int(value.decode() if isinstance(value, bytes) else value)
        except Exception:
            current = 0
        current += 1
        self.store[key] = str(current).encode("utf-8")
        print(f"[DEBUG][MockRedis.incr] Updated {key} to {current}")
        return current 