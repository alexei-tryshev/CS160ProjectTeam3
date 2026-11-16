from typing import Any, Dict, List, Optional

GOALS = {
    "cut": {"label": "Lose fat (cut)", "calorie_change": -500, "protein_per_lb": 1.0},
    "maintain": {"label": "Maintain", "calorie_change": 0, "protein_per_lb": 0.8},
    "bulk": {"label": "Build muscle (bulk)", "calorie_change": 300, "protein_per_lb": 1.0},
}

# Calories per pound of body weight to maintain weight at each activity level.
ACTIVITY_LEVELS = {
    "light": {"label": "Light (1-2 workouts a week)", "calories_per_lb": 13},
    "moderate": {"label": "Moderate (3-4 workouts a week)", "calories_per_lb": 15},
    "high": {"label": "High (5+ workouts a week)", "calories_per_lb": 17},
}

FAT_SHARE = 0.25          # share of calories that comes from fat
MIN_WEIGHT_LB = 70
MAX_WEIGHT_LB = 700
MIN_CALORIES = 1200       # never suggest a plan below this

# Simple meal ideas with approximate macros per serving.
MEAL_IDEAS: List[Dict[str, Any]] = [
    {"name": "Greek yogurt with berries and granola", "calories": 320, "protein_g": 22, "carbs_g": 42, "fat_g": 7},
    {"name": "Chicken, rice, and broccoli bowl", "calories": 520, "protein_g": 42, "carbs_g": 60, "fat_g": 10},
    {"name": "Egg and veggie scramble with toast", "calories": 380, "protein_g": 24, "carbs_g": 30, "fat_g": 18},
    {"name": "Turkey and avocado wrap", "calories": 450, "protein_g": 30, "carbs_g": 38, "fat_g": 18},
    {"name": "Salmon with sweet potato and greens", "calories": 560, "protein_g": 38, "carbs_g": 45, "fat_g": 22},
    {"name": "Protein shake with banana", "calories": 280, "protein_g": 27, "carbs_g": 35, "fat_g": 4},
    {"name": "Tofu stir-fry with noodles", "calories": 490, "protein_g": 26, "carbs_g": 62, "fat_g": 15},
    {"name": "Oatmeal with peanut butter", "calories": 400, "protein_g": 14, "carbs_g": 52, "fat_g": 16},
    {"name": "Tuna salad on whole-grain crackers", "calories": 330, "protein_g": 28, "carbs_g": 24, "fat_g": 13},
    {"name": "Cottage cheese with pineapple", "calories": 210, "protein_g": 24, "carbs_g": 20, "fat_g": 3},
]

MACRO_FIELDS = ("protein_g", "carbs_g", "fat_g")


def validate_plan(form: Dict[str, Any]) -> (Optional[Dict[str, Any]], List[str]):
    """Turn submitted form values into a plan dict, or return error messages."""
    errors = []
    goal = form.get("goal", "")
    activity = form.get("activity", "")
    if goal not in GOALS:
        errors.append("Choose a goal.")
    if activity not in ACTIVITY_LEVELS:
        errors.append("Choose an activity level.")
    try:
        weight_lb = float(form.get("weight_lb", ""))
        if not MIN_WEIGHT_LB <= weight_lb <= MAX_WEIGHT_LB:
            raise ValueError
    except (TypeError, ValueError):
        errors.append(
            "Weight must be a number from {} to {} lb.".format(MIN_WEIGHT_LB, MAX_WEIGHT_LB)
        )
        weight_lb = None
    if errors:
        return None, errors
    return {"goal": goal, "activity": activity, "weight_lb": round(weight_lb, 1)}, []


def daily_targets(plan: Dict[str, Any]) -> Dict[str, float]:
    """Calories and macro grams per day for a validated plan."""
    goal = GOALS[plan["goal"]]
    activity = ACTIVITY_LEVELS[plan["activity"]]
    weight = plan["weight_lb"]

    calories = weight * activity["calories_per_lb"] + goal["calorie_change"]
    calories = max(calories, MIN_CALORIES)

    protein_g = weight * goal["protein_per_lb"]
    fat_g = calories * FAT_SHARE / 9
    carbs_g = max((calories - protein_g * 4 - fat_g * 9) / 4, 0)

    return {
        "calories": round(calories),
        "protein_g": round(protein_g),
        "carbs_g": round(carbs_g),
        "fat_g": round(fat_g),
    }


def remaining(targets: Dict[str, float], eaten: Dict[str, float]) -> Dict[str, float]:
    """What is left today (never below zero)."""
    return {
        key: max(round(targets[key] - eaten.get(key, 0), 1), 0)
        for key in targets
    }


def percent_of_target(targets: Dict[str, float], eaten: Dict[str, float]) -> Dict[str, int]:
    """Progress toward each target, capped at 100 for the progress bars."""
    result = {}
    for key, target in targets.items():
        share = eaten.get(key, 0) / target * 100 if target else 0
        result[key] = int(min(round(share), 100))
    return result


def suggest_meals(left: Dict[str, float], limit: int = 3) -> List[Dict[str, Any]]:
    """Meals that fit in the calories left, highest protein first."""
    fits = [meal for meal in MEAL_IDEAS if meal["calories"] <= left["calories"]]
    if left.get("protein_g", 0) > 0:
        fits.sort(key=lambda meal: meal["protein_g"] / meal["calories"], reverse=True)
    else:
        fits.sort(key=lambda meal: meal["calories"])
    return fits[:limit]