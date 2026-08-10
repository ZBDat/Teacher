#!/usr/bin/env bash
# 在 0.0.0.0:8848 启动应用
set -euo pipefail
exec streamlit run streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port 9999 \
  --server.headless true
