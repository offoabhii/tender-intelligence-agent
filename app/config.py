"""
Central configuration.

This file is inside app/ so imports work consistently on:
- Windows
- GitHub Actions
- Streamlit Cloud
"""

from datetime import date

TODAY = date.today()
CURRENT_YEAR = TODAY.year

# Employer-approved categories only.
CATEGORIES_ALLOWED = [
    "Charging point operations",
    "Solar",
    "Bus operations (gross cost only)",
    "Bus body building",
]

BUS_OPERATIONS_CATEGORY = "Bus operations (gross cost only)"

# The company profile was not supplied.
# Therefore eligibility must stay NOT SURE unless it can be proven.
COMPANY_PROFILE = """
Company capability information is not available.

Rules:
- Never claim the company is eligible unless the source clearly proves it.
- Never invent turnover, certificates, fleet size, registrations,
  licences, experience, project capacity, or financial data.
- If eligibility cannot be proven, return NOT SURE.
"""

# Real web-search queries passed to Tavily.
SEARCHES = {
    "Charging point operations": (
        f'India government tender {CURRENT_YEAR} '
        '"EV charging station" operation maintenance O&M '
        'open tender site:gov.in OR site:nic.in'
    ),
    "Solar": (
        f'India government tender {CURRENT_YEAR} '
        'solar rooftop solar power plant installation '
        'operation maintenance O&M open tender '
        'site:gov.in OR site:nic.in'
    ),
    "Bus operations (gross cost only)": (
        f'India government tender {CURRENT_YEAR} '
        '"bus operations" "gross cost" contract open tender '
        'site:gov.in OR site:nic.in'
    ),
    "Bus body building": (
        f'India government tender {CURRENT_YEAR} '
        '"bus body" building fabrication manufacture supply '
        'open tender site:gov.in OR site:nic.in'
    ),
}

# Free-tier friendly: 5 results per category.
TAVILY_RESULTS_PER_CATEGORY = 5
