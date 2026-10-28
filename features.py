from typing import Any, Dict


DEFAULT_USER_ID = "demo-user"

DEFAULT_WATER_GOAL_OZ = 64

FEATURES: Dict[str, Dict[str, Any]] = {
    "nutrition": {
        "label": "Nutrition tracking",
        "description": "Record a food item and its nutrition values for a date.",
        "fields": [
            {"name": "food", "label": "Food", "type": "text", "required": True},
            {"name": "calories", "label": "Calories", "type": "number", "required": True, "step": "0.1"},
            {"name": "protein_g", "label": "Protein (g)", "type": "number", "required": True, "step": "0.1"},
            {"name": "carbs_g", "label": "Carbohydrates (g)", "type": "number", "required": True, "step": "0.1"},
            {"name": "fat_g", "label": "Fat (g)", "type": "number", "required": True, "step": "0.1"},
            {"name": "date", "label": "Date", "type": "date", "required": True},
        ],
    },
    "water": {
        "label": "Water intake tracking",
        "description": "Record the amount of water consumed on a date.",
        "fields": [
            {"name": "amount_oz", "label": "Amount (fl oz)", "type": "number", "required": True, "step": "1"},
            {"name": "date", "label": "Date", "type": "date", "required": True},
        ],
    },
    "steps": {
        "label": "Fitness logging",
        "description": "Record the number of steps completed on a date.",
        "fields": [
            {"name": "steps", "label": "Steps", "type": "number", "required": True, "step": "1"},
            {"name": "date", "label": "Date", "type": "date", "required": True},
        ],
    },
    "weight": {
        "label": "Weight tracking",
        "description": "Record a body-weight measurement on a date.",
        "fields": [
            {"name": "weight_lb", "label": "Weight (lb)", "type": "number", "required": True, "step": "0.1"},
            {"name": "date", "label": "Date", "type": "date", "required": True},
        ],
    },
}


def normalize_feature(feature: str) -> str:
    return "steps" if feature == "fitness" else feature