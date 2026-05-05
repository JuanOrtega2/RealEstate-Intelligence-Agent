from typing import Any, Dict

import requests
from ddgs import DDGS

from src.core.mcp import mcp
from src.core.models import InvestmentAnalysisInput

# Master data tables for Spanish market
ITP_RATES = {
    "Andalucía": 0.07,
    "Aragón": 0.08,
    "Asturias": 0.08,
    "Baleares": 0.08,
    "Canarias": 0.065,
    "Cantabria": 0.1,
    "Castilla - La Mancha": 0.09,
    "Castilla León": 0.08,
    "Cataluña": 0.1,
    "Ceuta": 0.06,
    "Comunidad de Madrid": 0.06,
    "Comunidad Valenciana": 0.1,
    "Extremadura": 0.08,
    "Galicia": 0.1,
    "La Rioja": 0.07,
    "Melilla": 0.06,
    "Murcia": 0.08,
    "Navarra": 0.06,
    "País Vasco": 0.04,
}

IRPF_TRAMS = [
    {"limit": 12450, "rate": 0.19},
    {"limit": 20200, "rate": 0.24},
    {"limit": 35200, "rate": 0.30},
    {"limit": 60000, "rate": 0.37},
    {"limit": float("inf"), "rate": 0.45},
]


def get_irpf_rate(salary: float) -> float:
    """Returns the IRPF tax bracket based on the annual gross salary."""
    for tram in IRPF_TRAMS:
        if salary <= tram["limit"]:
            return tram["rate"]
    return 0.45


def calculate_mortgage_details(
    amount: float, annual_rate: float, years: int
) -> Dict[str, float]:
    """Calculates mortgage details using the French Amortization System."""
    if amount <= 0 or years <= 0:
        return {"monthly_payment": 0, "annual_interest": 0, "annual_amortization": 0}

    # Robustness: Correct percentage vs decimal
    if annual_rate > 1:
        annual_rate = annual_rate / 100

    # Market Safety Floor: 3.0% minimum for realistic simulation
    if amount > 0 and annual_rate <= 0:
        annual_rate = 0.03

    monthly_rate = annual_rate / 12
    num_payments = years * 12

    if monthly_rate == 0:
        monthly_payment = amount / num_payments
    else:
        monthly_payment = (
            amount
            * (monthly_rate * (1 + monthly_rate) ** num_payments)
            / ((1 + monthly_rate) ** num_payments - 1)
        )

    remaining_balance = amount
    total_interest_year = 0
    total_amortization_year = 0

    for _ in range(12):
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        total_interest_year += interest_payment
        total_amortization_year += principal_payment
        remaining_balance -= principal_payment

    return {
        "monthly_payment": monthly_payment,
        "annual_interest": total_interest_year,
        "annual_amortization": total_amortization_year,
    }


@mcp.tool()
def search_market_data(query: str) -> str:
    """
    Performs a semantic web search using DuckDuckGo to find up-to-date market data
    (e.g., rental prices in a specific neighborhood, average yields).
    Ideal to use when the user asks to estimate data.
    """
    try:
        # SEO Hack: Force DDG to return statistical pages which contain the
        # exact €/m2 in the snippet.
        optimized_query = f"{query} evolucion precio alquiler m2 idealista brainsre"

        results = DDGS().text(optimized_query, max_results=5, region="es-es")
        if not results:
            return "No market data found on the web."

        extracted_info = []
        for r in results:
            extracted_info.append(f"Title: {r.get('title')}\nExtract: {r.get('body')}")

        return "\n\n".join(extracted_info)
    except Exception as e:
        return f"Web search error: {str(e)}"


@mcp.tool()
def read_property_link(url: str) -> str:
    """
    Attempts to read the content of a real estate link (e.g., Idealista, Fotocasa)
    using the Jina Reader engine. If it fails due to anti-bot blocks, it
    returns 'ERROR_SCRAPING_FAILED'.
    """
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url, timeout=10)

        # Detect blocks (403, Captcha, Access Denied)
        text = response.text
        if (
            response.status_code != 200
            or "Access Denied" in text
            or "Captcha" in text
            or "Attention Required!" in text
        ):
            return "ERROR_SCRAPING_FAILED"

        return text[
            :3000
        ]  # Extract first 3000 characters (usually contains price and m2)
    except Exception:
        return "ERROR_SCRAPING_FAILED"


@mcp.tool()
def analyze_investment_roi(data: InvestmentAnalysisInput) -> Dict[str, Any]:
    """
    Performs a high-precision Real Estate ROI analysis tailored for the
    Spanish market. This tool serves as the financial core of the agent,
    calculating profitability, tax impacts (IRPF), and debt metrics.

    MANDATORY INPUTS & SCHEMA DETAILS:
    - property_info (PropertyData):
        * purchase_price: (Required) Sales price of the asset. Must be > 0.
        * autonomous_community: (Required) Name of the Spanish community
          (e.g., "Madrid", "Andalucía") to apply the correct ITP tax rate.
        * renovation_costs: (Required) Initial capital for repairs.
    - rental_info (RentalData):
        * monthly_rent: (Required) Total monthly income. CRITICAL: The agent must
          factor in m2 price and room count before sending this value.
    - annual_expenses (AnnualExpensesData):
        * community_fees: (Required) Monthly HOA fees * 12. Must be realistic.
        * ibi_tax: (Required) Annual property tax. Estimate as 0.1% of price.
        * maintenance_costs: (Required) Annual upkeep. Estimate as 1% of rent.
        * vacancy_months: (Required) Number of months empty. Default to 1.
        * insurance: (Required) Home and (if applicable) Life insurance.
    - financing_info (FinancingData):
        * financing_percentage: (Required if financed) % of price financed.
        * mortgage_conditions: (Required if financed) Interest rate and term.

    KPI DEFINITIONS & CALCULATION LOGIC:
    1. Gross Yield: (Annual Gross Rent / Purchase Price) * 100.
    2. Cap Rate (Asset Quality): (Net Operating Income / Purchase Price) * 100.
       * NOI = Gross Rent - (IBI + Community + Maintenance + Insurances + Vacancy).
    3. Net Yield (Investor Yield): (Annual Cashflow Post-Debt / Purchase Price) * 100.
    4. Cash on Cash (CoC): (Annual Cashflow / Initial Equity Invested) * 100.
       * Equity = (Price * (1 - Financing%)) + ITP + Notary + Registry + Reform.
    5. ROCE (Total Return): ((Annual Cashflow + Amortization) / Equity) * 100.
       * This measures total wealth creation, not just liquid cash.
    6. Payback: Years needed to recover the 'Equity' through 'Annual Cashflow'.

    OUTPUT MANIFEST & RESPONSE STRUCTURE:
    The tool returns a dictionary with three main sections:
    - kpis: High-level metrics (yields, cap_rate, coc, roce, payback).
    - taxation: Detailed tax report (IRPF rate, taxes, fiscal_notes).
    - breakdown: Granular economic data (Opex, Mortgage, Initial Cash).

    STRICT FISCAL RULES (SPAIN):
    - IRPF Reduction: Applies a 60% reduction to the Net Rental Profit.
    - Docstrings: The agent must explain this reduction to avoid confusion.
    """
    # 1. Acquisition Costs
    community = data.property_info.autonomous_community
    itp_rate = ITP_RATES.get(community, 0.08)
    itp_tax = (
        data.property_info.itp_ajd_paid
        if data.property_info.itp_ajd_paid is not None
        else (data.property_info.purchase_price * itp_rate)
    )

    total_acquisition_costs = (
        itp_tax
        + data.property_info.notary_fees
        + data.property_info.registry_fees
        + data.property_info.renovation_costs
        + data.property_info.agency_commission
        + data.mortgage_setup.management_fees
        + data.mortgage_setup.appraisal_fees
        + data.mortgage_setup.opening_fee
    )

    # 2. Financing Details
    purchase_price = data.property_info.purchase_price
    loan_amount = purchase_price * (data.financing_info.financing_percentage / 100)
    equity_invested = (purchase_price - loan_amount) + total_acquisition_costs

    mortgage = {"monthly_payment": 0, "annual_interest": 0, "annual_amortization": 0}
    if data.financing_info.mortgage_conditions:
        mortgage = calculate_mortgage_details(
            loan_amount,
            data.financing_info.mortgage_conditions.annual_interest_rate,
            data.financing_info.mortgage_conditions.term_years,
        )

    # 3. Income and Operating Expenses
    vacancy_factor = (12 - data.annual_expenses.vacancy_months) / 12
    annual_gross_income = data.rental_info.monthly_rent * 12 * vacancy_factor

    annual_op_expenses = (
        data.annual_expenses.community_fees
        + data.annual_expenses.maintenance_costs
        + data.annual_expenses.home_insurance
        + data.annual_expenses.life_insurance
        + data.annual_expenses.default_insurance
        + data.annual_expenses.ibi_tax
    )

    net_operating_income = annual_gross_income - annual_op_expenses

    # 4. Taxation (IRPF)
    # Deductible: OPEX + Interests
    interest = mortgage["annual_interest"]
    taxable_profit_base = annual_gross_income - annual_op_expenses - interest

    # Applying 60% reduction for long-term rental
    irpf_rate = get_irpf_rate(data.investor_gross_salary)
    annual_taxes = max(0, taxable_profit_base * 0.4 * irpf_rate)

    # 5. CASH FLOW (Economic view)
    annual_mortgage_payment = mortgage["monthly_payment"] * 12
    annual_cash_profit = net_operating_income - annual_mortgage_payment - annual_taxes

    # 6. Final KPIs (The User's Trilogy)
    # Cap Rate: (Ingresos - Gastos) / Precio
    cap_rate = (net_operating_income / purchase_price) * 100

    # Net Yield: (Ingresos - Gastos - Hipoteca) / Precio
    net_yield_base = net_operating_income - annual_mortgage_payment
    net_yield = (net_yield_base / purchase_price) * 100

    # Cash on Cash: Annual Cashflow / Initial Equity
    coc_base = annual_cash_profit / equity_invested if equity_invested > 0 else 0
    cash_on_cash = coc_base * 100

    # ROCE (Total Return): (Cash Flow + Amortization) / Equity
    amortization = mortgage["annual_amortization"]
    roce_base = (
        (annual_cash_profit + amortization) / equity_invested
        if equity_invested > 0
        else 0
    )
    roce = roce_base * 100

    payback_years = (
        round(equity_invested / annual_cash_profit, 1)
        if annual_cash_profit > 0
        else "Sin payback (Cashflow ≤ 0)"
    )

    return {
        "kpis": {
            "gross_yield": round((annual_gross_income / purchase_price) * 100, 2),
            "cap_rate": round(cap_rate, 2),
            "net_yield": round(net_yield, 2),
            "cash_on_cash": round(cash_on_cash, 2),
            "roce": round(roce, 2),
            "payback_years": payback_years,
        },
        "taxation": {
            "marginal_irpf_rate": f"{round(irpf_rate * 100, 1)}%",
            "annual_taxes": round(annual_taxes, 2),
            "taxable_profit_legal_base": round(taxable_profit_base, 2),
            "fiscal_notes": (
                "Se ha aplicado la reducción estatal del 60% sobre el rendimiento "
                "neto positivo por alquiler de vivienda habitual a largo plazo "
                "(base imponible * 0.4)."
            ),
        },
        "breakdown": {
            "annual_gross_income": round(annual_gross_income, 2),
            "net_operating_income": round(net_operating_income, 2),
            "annual_mortgage_payment": round(annual_mortgage_payment, 2),
            "annual_mortgage_amortization": round(amortization, 2),
            "total_initial_cash_required": round(equity_invested, 2),
            "net_cash_flow_after_taxes": round(annual_cash_profit, 2),
        },
    }
