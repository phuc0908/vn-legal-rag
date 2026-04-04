"""
Root conftest.py — chạy từ thư mục backend/
"""
import sys
import os

# Đảm bảo backend/ có trong sys.path để import app.* hoạt động đúng
sys.path.insert(0, os.path.dirname(__file__))
