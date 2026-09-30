import time
import os
import requests
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:5001")

ORDER_COUNT = Counter('order_requests_total', 'Total order requests', ['status'])
ORDER_LATENCY = Histogram('order_request_duration_seconds', 'Order request latency')

@app.route("/healthz", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/orders", methods=["POST"])
def create_order():
    start_time = time.time()
    try:
        response = requests.post(f"{PAYMENT_SERVICE_URL}/process-payment", timeout=2.0)
        duration = time.time() - start_time
        ORDER_LATENCY.observe(duration)
        
        if response.status_code == 200:
            ORDER_COUNT.labels(status="200").inc()
            return jsonify({"order_id": "ORD-123", "status": "completed"}), 201
        else:
            ORDER_COUNT.labels(status="500").inc()
            return jsonify({"error": "Downstream payment failed"}), 502

    except requests.exceptions.RequestException:
        duration = time.time() - start_time
        ORDER_LATENCY.observe(duration)
        ORDER_COUNT.labels(status="504").inc()
        return jsonify({"error": "Payment service unreachable"}), 504

@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
