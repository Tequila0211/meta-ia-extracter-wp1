"""
Post-processing module for rules-based computation of effect sizes and meta-analysis eligibility.
Does not use AI.
"""

from typing import Any
from sqlalchemy.orm import Session

from src.database.models import Outcome, Scenario
from src.utils.logging_config import get_logger

logger = get_logger("export")

# Metrics where HIGHER values are better. Default is False (lower is better).
HIGHER_IS_BETTER_MAP = {
    "cooling_demand": False,
    "heating_demand": False,
    "total_energy_use": False,
    "carbon_emissions": False,
    "discomfort_hours": False,
    "indoor_temperature": False,
    "MPMV": False, # Deviation from comfort is bad
    "HIHH": False,
    "IOD": False,
    "HE": False,
    "WBGT": False,
    "HI": False,
    "comfort_hours": True,
    "cop": True,
    "efficiency": True,
    "spf": True,
}


def get_higher_is_better(outcome_name: str) -> bool:
    """Determine if higher is better for a given outcome name."""
    name_lower = outcome_name.lower()
    for key, val in HIGHER_IS_BETTER_MAP.items():
        if key in name_lower:
            return val
    return False  # Default to lower is better (energy, temperature, discomfort, etc.)


def compute_document_effect_sizes(session: Session, document_id: str) -> None:
    """Compute and update effect sizes for all outcomes of a document in the database.

    Args:
        session: SQLAlchemy session.
        document_id: Document ID.
    """
    outcomes = session.query(Outcome).filter(Outcome.document_id == document_id).all()
    logger.info(f"Computing effect sizes for {len(outcomes)} outcomes in document {document_id}")

    for outcome in outcomes:
        # Determine higher_is_better
        higher_better = get_higher_is_better(outcome.outcome_name)
        outcome.higher_is_better = 1 if higher_better else 0

        # Try to resolve baseline value and intervention value
        baseline_val = outcome.baseline_value
        if baseline_val is None:
            baseline_val = outcome.comparison_baseline_value

        intervention_val = outcome.intervention_value
        if intervention_val is None:
            # For outcomes, if this is an intervention scenario, the 'value' is the intervention value.
            intervention_val = outcome.value

        # If baseline value is still missing, try to resolve it from the linked baseline scenario's outcomes
        scenario = outcome.scenario
        if baseline_val is None and scenario and scenario.baseline_scenario_temp_id:
            # Find baseline scenario
            baseline_scenario = session.query(Scenario).filter(
                Scenario.document_id == document_id,
                Scenario.scenario_temp_id == scenario.baseline_scenario_temp_id
            ).first()

            if baseline_scenario:
                # Find outcome in baseline scenario with the same name and spatial scope
                baseline_outcome = session.query(Outcome).filter(
                    Outcome.document_id == document_id,
                    Outcome.scenario_id == baseline_scenario.id,
                    Outcome.outcome_name == outcome.outcome_name,
                    Outcome.room_or_space == outcome.room_or_space
                ).first()

                if baseline_outcome:
                    baseline_val = baseline_outcome.value
                    logger.debug(f"Resolved baseline value {baseline_val} from scenario {baseline_scenario.scenario_temp_id}")

        # Update resolved values in DB
        outcome.baseline_value = baseline_val
        outcome.intervention_value = intervention_val

        # If both are available, calculate effects
        if baseline_val is not None and intervention_val is not None:
            mean_diff = intervention_val - baseline_val
            pct_change = None
            if baseline_val != 0:
                pct_change = (mean_diff / baseline_val) * 100
            ratio = None
            if baseline_val != 0:
                ratio = intervention_val / baseline_val

            # Store primary calculated effect size
            # We will use mean_difference by default, or percent_change if requested
            outcome.calculated_effect_value = mean_diff
            outcome.calculated_effect_type = "mean_difference"
            outcome.is_ai_calculated = 1
            
            basis = f"Resolved: baseline={baseline_val}, intervention={intervention_val}. "
            basis += f"MD={mean_diff:.4f}"
            if pct_change is not None:
                basis += f", PctChange={pct_change:.2f}%"
            if ratio is not None:
                basis += f", Ratio={ratio:.4f}"
            outcome.ai_calculation_basis = basis

            # Standardized direction
            if higher_better:
                if mean_diff > 0:
                    outcome.effect_direction_standardized = "beneficial"
                elif mean_diff < 0:
                    outcome.effect_direction_standardized = "harmful"
                else:
                    outcome.effect_direction_standardized = "neutral"
            else:
                if mean_diff < 0:
                    outcome.effect_direction_standardized = "beneficial"
                elif mean_diff > 0:
                    outcome.effect_direction_standardized = "harmful"
                else:
                    outcome.effect_direction_standardized = "neutral"

            # Eligibility for meta-analysis
            method = outcome.extraction_method or "text"
            if method in ("figure_visual_approximate", "figure_visual_confident"):
                outcome.usable_for_quantitative_synthesis = 0
                outcome.usable_for_sensitivity_only = 1
            elif method in ("text", "table", "figure_digitized", "calculated"):
                outcome.usable_for_quantitative_synthesis = 1
                outcome.usable_for_sensitivity_only = 0
            else:
                outcome.usable_for_quantitative_synthesis = 0
                outcome.usable_for_sensitivity_only = 0
        else:
            # Cannot calculate effect size
            outcome.calculated_effect_value = None
            outcome.calculated_effect_type = "not_calculable"
            outcome.is_ai_calculated = 1
            outcome.ai_calculation_basis = "Missing baseline or intervention value."
            outcome.effect_direction_standardized = "unclear"
            outcome.usable_for_quantitative_synthesis = 0
            outcome.usable_for_sensitivity_only = 0

    session.flush()
