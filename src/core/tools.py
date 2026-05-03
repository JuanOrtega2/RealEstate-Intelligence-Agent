from typing import Any, Dict

from src.core.mcp import mcp
from src.core.models import InvestmentAnalysisInput

# Master data tables for Spanish market
ITP_RATES = {
    "Andalucía": 0.08,
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
    """Calculates the monthly payment and first-year amortization (French System)."""
    if amount <= 0 or years <= 0:
        return {"monthly_payment": 0, "annual_interest": 0, "annual_amortization": 0}

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
def analyze_investment_roi(data: InvestmentAnalysisInput) -> Dict[str, Any]:
    """
    Performs a professional Real Estate ROI analysis using structured
    English data blocks.

    Inputs:
    - property_info: Price, location, and acquisition fees.
    - mortgage_setup: Gestoria, appraisal, etc.
    - rental_info: Monthly rent.
    - annual_expenses: Maintenance, taxes, insurance, vacancy.
    - financing_info: Loan details.
    """
    # 1. Tax Calculation (ITP)
    community = data.property_info.autonomous_community
    itp_rate = ITP_RATES.get(community, 0.08)
    itp_tax = (
        data.property_info.itp_ajd_paid
        if data.property_info.itp_ajd_paid is not None
        else (data.property_info.purchase_price * itp_rate)
    )

    # 2. Total Initial Costs
    acquisition_costs = (
        itp_tax
        + data.property_info.notary_fees
        + data.property_info.registry_fees
        + data.property_info.renovation_costs
        + data.property_info.agency_commission
        + data.mortgage_setup.management_fees
        + data.mortgage_setup.appraisal_fees
        + data.mortgage_setup.opening_fee
    )

    # 3. Financing
    loan_amount = data.property_info.purchase_price * (
        data.financing_info.financing_percentage / 100
    )
    equity = data.property_info.purchase_price - loan_amount
    total_cash_out = equity + acquisition_costs

    mortgage = {"monthly_payment": 0, "annual_interest": 0, "annual_amortization": 0}
    if data.financing_info.mortgage_conditions:
        mortgage = calculate_mortgage_details(
            loan_amount,
            data.financing_info.mortgage_conditions.annual_interest_rate,
            data.financing_info.mortgage_conditions.term_years,
        )

    # 4. Operations
    vacancy_factor = (12 - data.annual_expenses.vacancy_months) / 12
    annual_gross_rent = data.rental_info.monthly_rent * 12 * vacancy_factor

    operating_expenses = (
        data.annual_expenses.community_fees
        + data.annual_expenses.maintenance_costs
        + data.annual_expenses.home_insurance
        + data.annual_expenses.life_insurance
        + data.annual_expenses.default_insurance
        + data.annual_expenses.ibi_tax
    )

    net_operating_income = annual_gross_rent - operating_expenses

    # 5. Taxation (IRPF)
    irpf_rate = get_irpf_rate(data.investor_gross_salary)
    taxable_income = net_operating_income - mortgage["annual_interest"]
    annual_taxes = max(0, taxable_income * 0.5 * irpf_rate)
    net_profit = net_operating_income - annual_taxes

    # 6. Cashflow
    annual_mortgage_payment = mortgage["monthly_payment"] * 12
    annual_cashflow = annual_gross_rent - operating_expenses - annual_mortgage_payment

    # 7. KPIs
    gross_yield = (
        data.rental_info.monthly_rent * 12 / data.property_info.purchase_price
    ) * 100
    net_yield = (net_operating_income / total_cash_out) * 100
    roce = (net_profit / total_cash_out) * 100

    return {
        "summary": {
            "gross_yield_percentage": round(gross_yield, 2),
            "net_yield_percentage": round(net_yield, 2),
            "annual_cashflow": round(annual_cashflow, 2),
            "roce_percentage": round(roce, 2),
        },
        "breakdown": {
            "total_cash_required": round(total_cash_out, 2),
            "loan_amount": round(loan_amount, 2),
            "monthly_mortgage_payment": round(mortgage["monthly_payment"], 2),
            "itp_tax_paid": round(itp_tax, 2),
            "annual_operating_expenses": round(operating_expenses, 2),
            "annual_irpf_taxes": round(annual_taxes, 2),
        },
    }
