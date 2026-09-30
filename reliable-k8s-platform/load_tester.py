import time
import requests
import concurrent.futures
import statistics

TARGET_URL = "http://localhost:5000/orders"
DURATION_SECONDS = 60
CONCURRENCY = 8

latencies = []
status_counts = {"success": 0, "fail": 0}

def worker(end_time):
    local_latencies = []
    local_success = 0
    local_fail = 0
    
    with requests.Session() as session:
        while time.time() < end_time:
            t0 = time.time()
            try:
                resp = session.post(TARGET_URL, timeout=3.0)
                elapsed = (time.time() - t0) * 1000  # in ms
                if resp.status_code in (200, 201):
                    local_success += 1
                else:
                    local_fail += 1
                local_latencies.append(elapsed)
            except Exception:
                local_fail += 1
    return local_success, local_fail, local_latencies

print(f"🔥 Starting load test on {TARGET_URL} for {DURATION_SECONDS}s with {CONCURRENCY} workers...")
start_time = time.time()
end_time = start_time + DURATION_SECONDS

with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    futures = [executor.submit(worker, end_time) for _ in range(CONCURRENCY)]
    for f in concurrent.futures.as_completed(futures):
        succ, fail, lats = f.result()
        status_counts["success"] += succ
        status_counts["fail"] += fail
        latencies.extend(lats)

total_reqs = status_counts["success"] + status_counts["fail"]
duration = time.time() - start_time
rps = round(total_reqs / duration, 2)
error_rate = round((status_counts["fail"] / total_reqs * 100), 2) if total_reqs else 0

latencies.sort()
p50 = round(statistics.median(latencies), 2) if latencies else 0
p95 = round(latencies[int(len(latencies) * 0.95)], 2) if latencies else 0
p99 = round(latencies[int(len(latencies) * 0.99)], 2) if latencies else 0

print("\n" + "="*35)
print("📊 LOAD TEST & RELIABILITY REPORT")
print("="*35)
print(f"Duration        : {round(duration, 2)} s")
print(f"Total Requests  : {total_reqs}")
print(f"Throughput      : {rps} req/s")
print(f"Success (2xx)   : {status_counts['success']}")
print(f"Failed  (5xx)   : {status_counts['fail']}")
print(f"Error Rate      : {error_rate} %")
print(f"p50 Latency     : {p50} ms")
print(f"p95 Latency     : {p95} ms")
print(f"p99 Latency     : {p99} ms")
print("="*35)