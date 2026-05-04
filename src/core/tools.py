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
    Performs a deep Real Estate ROI analysis with all financial metrics
    for the Spanish market.
    """
    # 1. Acquisition Costs
    community = data.property_info.autonomous_community
    itp_rate = ITP_RATES.get(community, 0.08)
    itp_tax = (
        data.property_info.itp_ajd_paid
        if data.property_info.itp_ajd_paid is not None
        else (data.property_info.purchase_price * itp_rate)
    )

    total_initial_expenses = (
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
    loan_amount = data.property_info.purchase_price * (
        data.financing_info.financing_percentage / 100
    )
    equity_invested = data.property_info.purchase_price - loan_amount
    total_cash_out = equity_invested + total_initial_expenses

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
    # Applying 50% reduction for long-term rental in Spain
    irpf_rate = get_irpf_rate(data.investor_gross_salary)
    taxable_profit = net_operating_income - mortgage["annual_interest"]
    annual_taxes = max(0, taxable_profit * 0.5 * irpf_rate)
    net_profit_after_taxes = net_operating_income - annual_taxes

    # 5. Debt Service and Cashflow
    annual_debt_service = mortgage["monthly_payment"] * 12
    annual_cashflow = annual_gross_income - annual_op_expenses - annual_debt_service

    # 6. Advanced KPIs
    gross_yield = (annual_gross_income / data.property_info.purchase_price) * 100
    net_yield = (net_operating_income / total_cash_out) * 100
    roce = (net_profit_after_taxes / total_cash_out) * 100

    # Payback period (Years to recover equity)
    payback_years = (
        total_cash_out / annual_cashflow if annual_cashflow > 0 else float("inf")
    )

    return {
        "kpis": {
            "gross_yield": round(gross_yield, 2),
            "net_yield": round(net_yield, 2),
            "annual_cashflow": round(annual_cashflow, 2),
            "roce": round(roce, 2),
            "payback_years": round(payback_years, 1),
        },
        "taxation": {
            "marginal_irpf_rate": round(irpf_rate * 100, 2),
            "annual_taxes": round(annual_taxes, 2),
            "taxable_profit_before_reduction": round(taxable_profit, 2),
        },
        "breakdown": {
            "annual_gross_income": round(annual_gross_income, 2),
            "net_operating_income_before_taxes": round(net_operating_income, 2),
            "annual_mortgage_amortization": round(mortgage["annual_amortization"], 2),
            "annual_mortgage_interest": round(mortgage["annual_interest"], 2),
            "total_initial_cash_required": round(total_cash_out, 2),
            "net_profit_after_taxes": round(net_profit_after_taxes, 2),
        },
    }
