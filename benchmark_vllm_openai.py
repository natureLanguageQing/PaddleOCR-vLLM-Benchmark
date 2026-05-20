#!/usr/bin/env python
import argparse
import base64
import json
import mimetypes
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def image_data_url(path):
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def post_json(url, payload, timeout):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    latency = time.perf_counter() - started
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        data = {"raw": raw.decode("utf-8", errors="replace")[:500]}
    return status, latency, data


def pct(values, percentile):
    values = sorted(values)
    index = round((percentile / 100) * (len(values) - 1))
    return values[index]


def main():
    parser = argparse.ArgumentParser(
        description="OpenAI-compatible concurrency benchmark for PaddleOCR-VL vLLM."
    )
    parser.add_argument("--image", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8081/v1/chat/completions")
    parser.add_argument("--model", default="PaddleOCR-VL-1.5-0.9B")
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--prompt", default="Recognize the text in this image.")
    args = parser.parse_args()

    payload = {
        "model": args.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": args.prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url(args.image)}},
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": args.max_tokens,
    }

    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(post_json, args.url, payload, args.timeout)
            for _ in range(args.requests)
        ]
        for future in as_completed(futures):
            status, latency, data = future.result()
            text = ""
            try:
                text = data["choices"][0]["message"]["content"].replace("\n", " ")[:120]
            except Exception:
                text = data.get("error", data.get("raw", "")) if isinstance(data, dict) else ""
            print(f"status={status} latency={latency:.2f}s text={text}")
            results.append((status, latency, data))

    elapsed = time.perf_counter() - started
    latencies = [item[1] for item in results]
    success = sum(1 for status, _, _ in results if status == 200)
    summary = {
        "requests": args.requests,
        "concurrency": args.concurrency,
        "success": success,
        "failed": len(results) - success,
        "elapsed_s": round(elapsed, 3),
        "throughput_rps": round(len(results) / elapsed, 4),
        "latency_avg_s": round(statistics.mean(latencies), 3),
        "latency_p50_s": round(pct(latencies, 50), 3),
        "latency_p95_s": round(pct(latencies, 95), 3),
        "latency_max_s": round(max(latencies), 3),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
