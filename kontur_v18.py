#!/usr/bin/env python3
"""Совместимость: `python kontur_v18.py ...` делегирует в пакет kontur."""

from kontur.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
