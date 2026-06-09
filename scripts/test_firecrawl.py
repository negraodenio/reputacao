"""
Quick smoke test for the Firecrawl integration.
Usage: python scripts/test_firecrawl.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from services.firecrawl_service import scrape

URL = "https://www.infomoney.com.br/perfil/thiago-nigro/"

print(f"Scraping: {URL}\n")
print("-" * 60)
text = scrape(URL)
print(text if text else "[empty — extraction failed or no content]")
print("-" * 60)
print(f"\nChars extracted: {len(text)}")
