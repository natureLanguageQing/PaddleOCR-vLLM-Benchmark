#!/usr/bin/env python
import argparse
import base64
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def encode_file(path):
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def post_json(url, payload, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
    latency = time.perf_counter() - start
    try:
        decoded = json.loads(body.decode("utf-8"))
    except Exception:
        decoded = {"raw": body.decode("utf-8", errors="replace")[:500]}
    return {
        "status": status,
        "latency_s": latency,
        "error_code": decoded.get("errorCode"),
        "error_msg": decoded.get("errorMsg"),
    }


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
    return ordered[idx]


def main():
    parser = argparse.ArgumentParser(
        description="Concurrency benchmark for PaddleOCR-VL-1.5 HPS Gateway."
    )
    parser.add_argument("--file", required=True, help="Input image or PDF path.")
    parser.add_argument("--url", default="http://localhost:8080/layout-parsing")
    parser.add_argument("--requests", type=int, default=16)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--no-visualization", action="store_true")
    args = parser.parse_args()

    payload = {"file": encode_file(args.file)}
    if args.no_visualization:
        payload["visualize"] = False

    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(post_json, args.url, payload, args.timeout)
            for _ in range(args.requests)
        ]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"status={result['status']} latency={result['latency_s']:.2f}s "
                f"errorCode={result['error_code']} errorMsg={result['error_msg']}"
            )

    elapsed = time.perf_counter() - started
    ok = [r for r in results if r["status"] == 200 and r["error_code"] in (0, None)]
    latencies = [r["latency_s"] for r in results]
    summary = {
        "requests": args.requests,
        "concurrency": args.concurrency,
        "success": len(ok),
        "failed": len(results) - len(ok),
        "elapsed_s": round(elapsed, 3),
        "throughput_rps": round(len(results) / elapsed, 4) if elapsed else None,
        "latency_avg_s": round(statistics.mean(latencies), 3) if latencies else None,
        "latency_p50_s": round(percentile(latencies, 50), 3) if latencies else None,
        "latency_p95_s": round(percentile(latencies, 95), 3) if latencies else None,
        "latency_max_s": round(max(latencies), 3) if latencies else None,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
