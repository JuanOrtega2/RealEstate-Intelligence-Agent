from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class PropertyData(BaseModel):
    """Data related to the property acquisition and initial costs."""

    purchase_price: float = Field(..., description="Property sales price")
    autonomous_community: str = Field(
        ..., description="Spanish Autonomous Community for tax (ITP) calculation"
    )
    itp_ajd_paid: Optional[float] = Field(
        None, description="ITP/AJD tax. Will be calculated if not provided."
    )
    notary_fees: float = Field(0.0, description="Notary fees for the purchase")
    registry_fees: float = Field(0.0, description="Registry fees for the purchase")
    renovation_costs: float = Field(0.0, description="Initial renovation/reform costs")
    agency_commission: float = Field(0.0, description="Real estate agency commission")


class MortgageSetupData(BaseModel):
    """Initial costs associated with setting up the mortgage."""

    management_fees: float = Field(
        0.0, description="Mortgage management fees (Gestoría)"
    )
    appraisal_fees: float = Field(0.0, description="Property appraisal fee (Tasación)")
    opening_fee: float = Field(0.0, description="Opening fee paid to the bank")


class RentalData(BaseModel):
    """Rental income data."""

    monthly_rent: float = Field(..., description="Estimated monthly rental income")


class AnnualExpensesData(BaseModel):
    """Annual operating expenses for the property."""

    community_fees: float = Field(0.0, description="Annual community fees")
    maintenance_costs: float = Field(0.0, description="Estimated annual maintenance")
    home_insurance: float = Field(0.0, description="Annual home insurance")
    life_insurance: float = Field(
        0.0, description="Annual life insurance (mortgage linked)"
    )
    default_insurance: float = Field(0.0, description="Annual rental default insurance")
    ibi_tax: float = Field(0.0, description="Annual property tax (IBI)")
    vacancy_months: int = Field(
        0, description="Number of months the property is expected to be vacant per year"
    )


class MortgageConditions(BaseModel):
    """Financial conditions of the mortgage loan."""

    annual_interest_rate: float = Field(
        0.0, description="Annual interest rate (decimal, e.g., 0.03 for 3%)"
    )
    term_years: int = Field(0, description="Mortgage term in years")


class FinancingData(BaseModel):
    """Data regarding how the investment is financed."""

    financing_percentage: float = Field(
        80.0, description="Percentage of the purchase price financed by the bank"
    )
    equity: Optional[float] = Field(
        None, description="Equity invested (Capital propio)"
    )
    mortgage_conditions: Optional[MortgageConditions] = Field(
        None, description="Detailed mortgage conditions"
    )


class InvestmentAnalysisInput(BaseModel):
    """Master input for the Real Estate ROI analysis."""

    property_info: PropertyData
    mortgage_setup: MortgageSetupData
    rental_info: RentalData
    annual_expenses: AnnualExpensesData
    financing_info: FinancingData
    investor_gross_salary: float = Field(
        30000.0, description="Gross annual salary for tax (IRPF) calculations"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_llm_null_quirks(cls, data: Any) -> Any:
        """
        Cleans the input data coming from the LLM.
        Replaces literal string "null" with None to prevent validation errors.
        """

        def _clean(v):
            if isinstance(v, dict):
                return {k: _clean(val) for k, val in v.items()}
            if isinstance(v, list):
                return [_clean(val) for val in v]
            if v == "null":
                return None
            return v

        if isinstance(data, dict):
            return _clean(data)
        return data
