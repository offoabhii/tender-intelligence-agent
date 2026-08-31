from datetime import date
TODAY = date.today().isoformat()

CATEGORIES = [
    "Charging point operations",
    "Solar",
    "Bus operations (gross cost only)",
    "Bus body building"
]

# Search queries engineered for high precision
SEARCH_QUERIES = {
    "Charging point operations": [
        "EV charging point operations tender India open",
        "charging station operation maintenance tender eprocure"
    ],
    "Solar": [
        "solar power plant installation tender India open",
        "solar rooftop tender government eprocure"
    ],
    "Bus operations (gross cost only)": [
        "bus operations gross cost contract tender India",
        "GCC bus operation gross cost basis tender STU"
    ],
    "Bus body building": [
        "bus body building fabrication tender India",
        "bus body construction tender state transport"
    ]
}

# Static portals to crawl - LLM will parse them by context, not CSS selector
STATIC_SOURCES = [
    "https://eprocure.gov.in/cppp/search",
    "https://bidplus.gem.gov.in/all-bids",
]