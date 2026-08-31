"""
Config - Final Working Version
"""
from datetime import datetime

# REAL SEARCH QUERIES (Proven to return results on Tavily)
SOURCES = {
    "charging": "site:nic.in OR site:gov.in electric vehicle charging station operation maintenance tender 2025 open",
    "solar": "site:mnre.gov.in OR site:nic.in solar rooftop installation O&M tender open 2025", 
    "bus_ops": "site:hry.nic.in OR site:tenders.gov.in bus operations gross cost contract transport tender open 2025",
    "bus_body": "site:acma.goa.gov.in OR site:tenders.gov.in bus body building fabrication supply tender 2025"
}

CATEGORIES_ALLOWED = [
    "Charging point operations",
    "Solar", 
    "Bus operations (gross cost only)",
    "Bus body building"
]

REJECT_NET_COST_CATEGORIES = ["Bus operations (gross cost only)"]
TODAY_DATE = datetime.now().strftime("%Y-%m-%d")
