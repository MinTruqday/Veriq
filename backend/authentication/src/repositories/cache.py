from src.core.infrastructure.redis import redis


class CacheRepository:
    @staticmethod
    async def count_patterns(patterns: list[str]):
        client = redis.get_client()
        total = 0
        for pattern in patterns:
            async for _ in client.scan_iter(match=pattern):
                total += 1
        return total

    @staticmethod
    async def delete_patterns(patterns: list[str]):
        client = redis.get_client()
        keys = []
        for pattern in patterns:
            keys.extend([key async for key in client.scan_iter(match=pattern)])
        if keys:
            await client.delete(*keys)
        return len(keys)
