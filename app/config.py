"""
Tender Intelligence Agent Configuration

Only these four business categories are allowed.
All other tenders are rejected.
"""

from datetime import date

TODAY = date.today()
CURRENT_YEAR = TODAY.year

# The employer's approved categories.
CATEGORIES_ALLOWED = [
    "Charging point operations",
    "Solar",
    "Bus operations (gross cost only)",
    "Bus body building",
]

# A Net Cost tender is never relevant for Bus Operations.
BUS_OPERATIONS_CATEGORY = "Bus operations (gross cost only)"

# IMPORTANT:
# This profile is intentionally conservative.
# If your company's actual capability details are unknown,
# the auditor must output NOT SURE instead of guessing eligibility.
COMPANY_PROFILE = """
Company eligibility information is not fully provided.

Therefore:
- Do NOT say ELIGIBLE unless source requirements clearly match the profile.
- If eligibility cannot be proven, return NOT SURE.
- Never invent fleet size, turnover, certifications, past experience,
  registration, state licenses, or technical qualifications.
"""

# Live Tavily queries.
# These are searches, not fake portal URLs.
# Tavily returns actual result URLs that are saved with every tender.
SEARCHES = {
    "Charging point operations": (
        f'India government tender "{CURRENT_YEAR}" '
        '"EV charging station" operation maintenance O&M '
        'open tender site:gov.in OR site:nic.in'
    ),
    "Solar": (
        f'India government tender "{CURRENT_YEAR}" '
        'solar rooftop solar power plant installation operation maintenance '
        'open tender site:gov.in OR site:nic.in'
    ),
    "Bus operations (gross cost only)": (
        f'India government tender "{CURRENT_YEAR}" '
        '"bus operations" "gross cost" contract open tender '
        'site:gov.in OR site:nic.in'
    ),
    "Bus body building": (
        f'India government tender "{CURRENT_YEAR}" '
        '"bus body" building fabrication manufacture supply open tender '
        'site:gov.in OR site:nic.in'
    ),
}

# Tavily free-tier friendly settings.
TAVILY_RESULTS_PER_CATEGORY = 5
