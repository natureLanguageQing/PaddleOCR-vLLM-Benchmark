# PaddleOCR-vLLM-Benchmark

This repository contains benchmarking scripts and testing datasets for evaluating **PaddleOCR-VL 1.5** (0.9B) performance with a **vLLM** backend.

English | [简体中文](./README_zh.md)

---

## 🖥️ Benchmark Environment & GPU Config

- **GPU**: NVIDIA GeForce RTX 4090 (24GB VRAM)
- **CUDA Version**: 13.2 / Driver 596.36
- **Model**: PaddleOCR-VL-1.5-0.9B
- **Framework**: vLLM OpenAI-Compatible Server (`temperature=0`)

---

## 📊 Key Performance Metrics

Below is a summary of the concurrency tests run on the RTX 4090 using an educational math exam paper image (~553 output tokens generated):

| Test Scenario | Total Requests | Concurrency | Avg Latency | Throughput (RPS) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline** | 20 | 8 | 1.57s | 4.33 RPS | Pass |
| **Heavy Payload (10.5MB Image)** | 16 | 4 | 1.30s | 2.89 RPS | Pass |
| **High Concurrency** | 64 | 32 | 2.80s | **10.57 RPS** | Pass |
| **Extreme Load** | 128 | 64 | 3.19s | **18.22 RPS** | Pass |

---

## 📄 Detailed Report & Architecture

For full analysis on VRAM usage, long context performance (up to `8192` tokens), and high-availability production deployment architecture (Nginx + Kafka queue), please refer to the complete report:

👉 **[Read the Full Benchmark & Servitization Report (paddleocr_vl_benchmark_report.md)](./paddleocr_vl_benchmark_report.md)**
