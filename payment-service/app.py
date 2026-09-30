import time
import os
import random
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# --- Prometheus Metrics ---
# Counter: A metric that only goes up (tracks total requests)
REQUEST_COUNT = Counter('payment_requests_total', 'Total HTTP requests', ['status'])
# Histogram: Tracks latency distributions (how fast or slow requests are)
REQUEST_LATENCY = Histogram('payment_request_duration_seconds', 'HTTP request latency')

# Chaos toggle: allows us to inject latency or crashes on demand
CHAOS_MODE = os.getenv("CHAOS_MODE", "false").lower() == "true"

@app.route("/healthz", methods=["GET"])
def health():
    """Liveness & Readiness probe endpoint for Kubernetes"""
    return jsonify({"status": "healthy"}), 200

@app.route("/process-payment", methods=["POST"])
def process_payment():
    start_time = time.time()
    
    # 💥 Simulated failure if Chaos Mode is enabled
    if CHAOS_MODE and random.random() < 0.4:
        # 40% chance of high latency or error
        time.sleep(2.0)
        REQUEST_COUNT.labels(status="500").inc()
        return jsonify({"error": "Payment gateway timeout"}), 500

    # Normal simulated processing time
    time.sleep(0.05) 
    
    duration = time.time() - start_time
    REQUEST_LATENCY.observe(duration)
    REQUEST_COUNT.labels(status="200").inc()
    
    return jsonify({"status": "payment_approved", "transaction_id": random.randint(1000, 9999)}), 200

@app.route("/metrics", methods=["GET"])
def metrics():
    """Exposes application metrics for Prometheus to scrape"""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)