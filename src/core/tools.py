from typing import Any, Dict

from src.core.mcp import mcp

# Master data tables extracted from the methodology Excel
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


@mcp.tool()
def get_irpf_rate(salary: float) -> float:
    """Returns the IRPF tax bracket based on the annual gross salary."""
    for tram in IRPF_TRAMS:
        if salary <= tram["limit"]:
            return tram["rate"]
    return 0.45


@mcp.tool()
def calculate_mortgage_details(
    amount: float, annual_rate: float, years: int
) -> Dict[str, float]:
    """Calculates the monthly payment and first-year amortization (French System)."""
    if amount <= 0:
        return {"monthly_payment": 0, "annual_interest": 0, "annual_amortization": 0}

    monthly_rate = annual_rate / 12
    num_payments = years * 12

    # French system formula: P * (r * (1+r)^n) / ((1+r)^n - 1)
    monthly_payment = (
        amount
        * (monthly_rate * (1 + monthly_rate) ** num_payments)
        / ((1 + monthly_rate) ** num_payments - 1)
    )

    # Simplified first-year estimation (Interest and Amortization)
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
def calculate_investment_metrics(
    purchase_price: float,
    community: str,
    monthly_rent: float,
    is_new_build: bool = False,
    reforma: float = 0,
    agencia: float = 0,
    notaria: float = 0,
    registro: float = 0,
    tasacion: float = 0,
    gestoria: float = 0,
    percent_financed: float = 80,
    mortgage_years: int = 30,
    mortgage_rate: float = 0.03,
    ibi: float = 0,
    comunidad_gastos: float = 0,
    seguro: float = 0,
    otros_gastos: float = 0,
    salario_bruto: float = 30000,
) -> Dict[str, Any]:
    """
    Calculates technical and financial KPIs for a real estate investment in Spain.

    IMPORTANT: This tool should ONLY be used when the user provides property
    data (price and rent) for a financial feasibility study.
    DO NOT use this tool for greetings or non-investment topics.

    - purchase_price: Property sales price.
    - community: Autonomous Community (CCAA) for ITP tax calculation.
    - monthly_rent: Estimated monthly rental income.
    - is_new_build: If True, applies 10% VAT instead of ITP tax.
    - reforma/agencia/notaria/registro/tasacion/gestoria: Acquisition costs.
    - ibi/comunidad_gastos/seguro/otros_gastos: Annual operating expenses.
    - salario_bruto: Investor's annual gross salary for tax calculation.

    OUTPUTS:
    - summary: Key KPIs (Gross Yield, Net Yield, Annual Cashflow, ROCE).
    - details: Breakdown of investment, taxes, mortgage, and net profit.
    """
    # Safety check to avoid division by zero
    if purchase_price <= 0:
        return {"error": "Purchase price must be > 0 to perform analysis."}

    # 1. Acquisition Taxes
    itp_rate = 0.10 if is_new_build else ITP_RATES.get(community, 0.08)
    itp_tax = purchase_price * itp_rate

    # 2. Total Investment (Capital Out)
    total_acquisition_costs = (
        itp_tax + notaria + registro + tasacion + gestoria + reforma + agencia
    )
    loan_amount = purchase_price * (percent_financed / 100)
    personal_funds_entry = purchase_price * (1 - percent_financed / 100)
    total_investment = personal_funds_entry + total_acquisition_costs

    # 3. Mortgage
    mortgage = calculate_mortgage_details(loan_amount, mortgage_rate, mortgage_years)

    # 4. Annual Operation
    annual_revenue = monthly_rent * 12
    annual_operating_expenses = ibi + comunidad_gastos + seguro + otros_gastos
    bai = annual_revenue - annual_operating_expenses

    # 5. Taxation (Excel Formula: (BAI - Amortization) * 0.5 * IRPF_Rate)
    irpf_rate = get_irpf_rate(salario_bruto)
    taxable_base = bai - mortgage["annual_amortization"]
    taxes = max(0, taxable_base * 0.5 * irpf_rate)
    net_profit = bai - taxes

    # 6. Cashflow (Rent - Op Expenses - Mortgage Payment)
    annual_mortgage_cost = mortgage["monthly_payment"] * 12
    annual_cashflow = annual_revenue - annual_operating_expenses - annual_mortgage_cost

    # 7. Final KPIs
    gross_yield = (annual_revenue / purchase_price) * 100
    net_yield = (bai / total_investment) * 100
    roce = (net_profit / total_investment) * 100

    return {
        "summary": {
            "gross_yield_percent": round(gross_yield, 2),
            "net_yield_percent": round(net_yield, 2),
            "annual_cashflow": round(annual_cashflow, 2),
            "roce_percent": round(roce, 2),
        },
        "details": {
            "total_investment": round(total_investment, 2),
            "monthly_mortgage": round(mortgage["monthly_payment"], 2),
            "itp_paid": round(itp_tax, 2),
            "taxes_paid": round(taxes, 2),
            "net_profit_annual": round(net_profit, 2),
        },
    }
