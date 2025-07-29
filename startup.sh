#!/bin/bash
playwright install chromium
gunicorn --bind=0.0.0.0 --timeout 1200 app:app