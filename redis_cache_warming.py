#!/usr/bin/env python3
"""Redis Cache Warming Script for Performance Optimization"""

import json
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️  Redis not installed. Install with: pip install redis")

class CacheWarmer:
    """Redis cache warming implementation"""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db

        if REDIS_AVAILABLE:
            try:
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.client.ping()
                print(f"✓ Connected to Redis at {host}:{port}/{db}")
            except Exception as e:
                print(f"✗ Redis connection failed: {e}")
                self.client = None
        else:
            self.client = None

    def warm_health_endpoint(self, ttl_seconds: int = 300):
        """Warm cache for health endpoint"""
        if not self.client:
            return

        print("\n🔥 Warming health endpoint cache...")
        cache_key = "cache:endpoint:health"

        try:
            data = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "uptime": "running"
            }

            self.client.setex(cache_key, ttl_seconds, json.dumps(data))
            print(f"  ✓ Cached {cache_key} (TTL: {ttl_seconds}s)")

        except Exception as e:
            print(f"  ✗ Failed to cache health: {e}")

    def warm_metrics_endpoint(self, ttl_seconds: int = 300):
        """Warm cache for metrics endpoint"""
        if not self.client:
            return

        print("\n🔥 Warming metrics endpoint cache...")
        cache_key = "cache:endpoint:metrics"

        try:
            metrics_data = {
                "requests_total": 0,
                "requests_active": 0,
                "response_time_avg_ms": 8.5,
                "error_rate_percent": 0.0,
                "last_updated": datetime.utcnow().isoformat()
            }

            self.client.setex(cache_key, ttl_seconds, json.dumps(metrics_data))
            print(f"  ✓ Cached {cache_key} (TTL: {ttl_seconds}s)")

        except Exception as e:
            print(f"  ✗ Failed to cache metrics: {e}")

    def warm_settings_cache(self, ttl_seconds: int = 600):
        """Warm cache for user settings"""
        if not self.client:
            return

        print("\n🔥 Warming settings cache...")

        # Sample settings structure
        settings_templates = [
            {
                "key": "settings:user:preferences",
                "value": {
                    "theme": "dark",
                    "language": "zh-CN",
                    "notifications": True,
                    "timezone": "Asia/Shanghai"
                }
            },
            {
                "key": "settings:api:defaults",
                "value": {
                    "default_limit": 20,
                    "max_pages": 100,
                    "timeout": 30
                }
            }
        ]

        for setting in settings_templates:
            try:
                key = f"cache:setting:{setting['key']}"
                self.client.setex(key, ttl_seconds, json.dumps(setting['value']))
                print(f"  ✓ Cached {key}")
            except Exception as e:
                print(f"  ✗ Failed to cache {setting['key']}: {e}")

    def warm_agent_list_cache(self, ttl_seconds: int = 600):
        """Warm cache for agent listing (frequently accessed)"""
        if not self.client:
            return

        print("\n🔥 Warming agent list cache...")

        cache_key = "cache:list:agents:recent"
        try:
            agents_sample = [
                {
                    "id": f"agent-{i}",
                    "name": f"Agent {i}",
                    "status": "active",
                    "updated_at": (datetime.utcnow() - timedelta(hours=i)).isoformat()
                }
                for i in range(min(50, 1000))  # Simulate last 50 agents
            ]

            self.client.setex(cache_key, ttl_seconds, json.dumps(agents_sample))
            print(f"  ✓ Cached recent agents list ({len(agents_sample)} items)")

        except Exception as e:
            print(f"  ✗ Failed to cache agents: {e}")

    def clear_all_caches(self):
        """Clear all cached data"""
        if not self.client:
            return

        print("\n🧹 Clearing all caches...")
        try:
            pattern = "cache:*"
            keys = self.client.keys(pattern)

            if keys:
                self.client.delete(*keys)
                print(f"  ✓ Cleared {len(keys)} cache entries")
            else:
                print("  ℹ️  No cached entries to clear")

        except Exception as e:
            print(f"  ✗ Clear cache failed: {e}")

    def get_cache_stats(self):
        """Get Redis cache statistics"""
        if not self.client:
            return

        try:
            info = self.client.info('memory')
            stats = {
                "used_memory": info.get('used_memory', 0),
                "used_memory_human": info.get('used_memory_human', 'N/A'),
                "peak_memory": info.get('peak_used_memory', 0),
                "hit_rate": "N/A"
            }

            print("\n📊 Cache Statistics:")
            print(f"  Used Memory: {stats['used_memory_human']}")
            print(f"  Peak Memory: {stats['peak_memory'] / 1024 / 1024:.2f} MB")

        except Exception as e:
            print(f"✗ Failed to get stats: {e}")


def main():
    """Main cache warming function"""
    print("="*80)
    print("REDIS CACHE WARMING UTILITY")
    print("="*80)

    warmer = CacheWarmer()

    if not warmer.client:
        print("\n⚠️  Skipping cache warming - Redis not available")
        return

    # Perform cache warming
    warmer.warm_health_endpoint(ttl_seconds=300)
    warmer.warm_metrics_endpoint(ttl_seconds=300)
    warmer.warm_settings_cache(ttl_seconds=600)
    warmer.warm_agent_list_cache(ttl_seconds=600)

    # Get final stats
    warmer.get_cache_stats()

    print("\n" + "="*80)
    print("✓ Cache warming completed!")
    print("="*80)


if __name__ == "__main__":
    main()
