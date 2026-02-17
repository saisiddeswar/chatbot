
from core.stats_manager import StatsManager
import os

print("Testing StatsManager...")

# 1. Check default
print("Defaults:", StatsManager.get_top_queries())

# 2. Increment
print("Incrementing 'Test Query'...")
StatsManager.increment_query_count("Test Query")
StatsManager.increment_query_count("Test Query")
StatsManager.increment_query_count("Another Query")

# 3. Check stats
top = StatsManager.get_top_queries(10)
print("Top Queries:", top)

# 4. Cleanup
if os.path.exists("data/query_stats.json"):
    print("Stats file created successfully.")
    # valid
else:
    print("ERROR: Stats file not created.")
