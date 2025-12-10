"""
Style Override System for Persona Configuration

This module implements the override-only injection system for persona styles.
Each category (Coach, Assistant, Friend, etc.) has default style values.
Only when a user explicitly changes a style from its category default
does the corresponding prompt text get injected into the LLM.

This keeps prompts clean while allowing fine-tuning when needed.
"""

from typing import Dict, List, Optional


# Category-specific default style values
# These represent the "natural" style for each persona category
CATEGORY_DEFAULTS: Dict[str, Dict[str, str]] = {
    "Coach": {
        "warmth": "neutral",
        "formality": "formal",
        "directness": "direct",
        "humor": "minimal",
    },
    "Assistant": {
        "warmth": "neutral",
        "formality": "formal",
        "directness": "balanced",
        "humor": "minimal",
    },
    "Friend": {
        "warmth": "warm",
        "formality": "casual",
        "directness": "balanced",
        "humor": "moderate",
    },
    "Teacher": {
        "warmth": "warm",
        "formality": "neutral",
        "directness": "balanced",
        "humor": "moderate",
    },
    "Advisor": {
        "warmth": "neutral",
        "formality": "formal",
        "directness": "direct",
        "humor": "minimal",
    },
    "Companion": {
        "warmth": "warm",
        "formality": "casual",
        "directness": "gentle",
        "humor": "playful",
    },
    "Roleplay": {
        "warmth": "neutral",
        "formality": "neutral",
        "directness": "balanced",
        "humor": "moderate",
    },
    "Creative": {
        "warmth": "warm",
        "formality": "casual",
        "directness": "gentle",
        "humor": "playful",
    },
    "Other": {
        "warmth": "neutral",
        "formality": "neutral",
        "directness": "balanced",
        "humor": "moderate",
    },
}

# Style dimension options (3-level scale for each)
STYLE_OPTIONS = {
    "warmth": ["cold", "neutral", "warm"],
    "formality": ["casual", "neutral", "formal"],
    "directness": ["gentle", "balanced", "direct"],
    "humor": ["minimal", "moderate", "playful"],
}

# Prompt text to inject when style differs from default
# Only the changed value's prompt gets added
STYLE_PROMPTS: Dict[str, Dict[str, str]] = {
    "warmth": {
        "cold": (
            "Maintain emotional distance in your responses. "
            "Be matter-of-fact and objective. Avoid expressions of personal warmth, "
            "excessive encouragement, or emotional support unless specifically requested."
        ),
        "neutral": "",  # Default for most categories - no override needed
        "warm": (
            "Be warm and supportive in your responses. "
            "Show genuine interest and care. Use encouraging language and "
            "acknowledge emotions when appropriate."
        ),
    },
    "formality": {
        "casual": (
            "Use casual, conversational language. "
            "Contractions, colloquialisms, and relaxed phrasing are appropriate. "
            "Avoid overly formal or stiff language."
        ),
        "neutral": "",  # No override needed
        "formal": (
            "Maintain professional, formal language. "
            "Use proper grammar, avoid contractions when possible, "
            "and keep responses structured and polished."
        ),
    },
    "directness": {
        "gentle": (
            "Be gentle and tactful in your communication. "
            "Soften feedback with supportive framing. Avoid blunt statements "
            "and prioritize the emotional impact of your words."
        ),
        "balanced": "",  # No override needed
        "direct": (
            "Be direct and straightforward. "
            "Get to the point quickly without excessive hedging or softening. "
            "Prioritize clarity and honesty over diplomatic phrasing."
        ),
    },
    "humor": {
        "minimal": (
            "Keep responses focused and serious. "
            "Avoid jokes, playful comments, or humorous asides unless the context clearly calls for levity."
        ),
        "moderate": "",  # No override needed
        "playful": (
            "Feel free to be playful and incorporate appropriate humor. "
            "Light jokes, wit, and playful observations are welcome when they fit the conversation."
        ),
    },
}

# Human-readable labels for UI display
STYLE_LABELS: Dict[str, Dict[str, str]] = {
    "warmth": {
        "cold": "Cold",
        "neutral": "Neutral",
        "warm": "Warm",
    },
    "formality": {
        "casual": "Casual",
        "neutral": "Neutral",
        "formal": "Formal",
    },
    "directness": {
        "gentle": "Gentle",
        "balanced": "Balanced",
        "direct": "Direct",
    },
    "humor": {
        "minimal": "Minimal",
        "moderate": "Moderate",
        "playful": "Playful",
    },
}

# Descriptions for UI tooltips
STYLE_DESCRIPTIONS: Dict[str, str] = {
    "warmth": "How emotionally warm or distant the persona is",
    "formality": "How formal or casual the language style is",
    "directness": "How blunt or tactful the communication is",
    "humor": "How much humor and playfulness to include",
}


def get_category_defaults(category: str) -> Dict[str, str]:
    """
    Get the default style values for a given category.

    Args:
        category: The persona category (Coach, Friend, etc.)

    Returns:
        Dictionary of style dimension -> default value
    """
    return CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["Other"]).copy()


def get_style_overrides(category: str, styles: Dict[str, str]) -> str:
    """
    Generate prompt text for styles that differ from category defaults.

    Only returns prompt text for styles the user has explicitly changed
    from the category's default values. This keeps prompts clean while
    allowing fine-tuning when needed.

    Args:
        category: The persona category (Coach, Friend, etc.)
        styles: Dictionary of style dimension -> user-selected value

    Returns:
        Combined prompt text for all overridden styles, or empty string if none
    """
    if not styles:
        return ""

    defaults = get_category_defaults(category)
    overrides: List[str] = []

    for style_name, user_value in styles.items():
        # Skip if style dimension is not recognized
        if style_name not in STYLE_PROMPTS:
            continue

        # Skip if value matches category default
        default_value = defaults.get(style_name)
        if user_value == default_value:
            continue

        # Skip if value is not valid for this dimension
        if user_value not in STYLE_PROMPTS[style_name]:
            continue

        # Get the prompt text for this override
        prompt_text = STYLE_PROMPTS[style_name][user_value]
        if prompt_text:  # Only add non-empty prompts
            overrides.append(prompt_text)

    if not overrides:
        return ""

    return "\n\n".join(overrides)


def get_changed_styles_count(category: str, styles: Dict[str, str]) -> int:
    """
    Count how many styles differ from category defaults.

    Useful for UI display (e.g., "4 changed from defaults").

    Args:
        category: The persona category
        styles: Dictionary of style dimension -> user-selected value

    Returns:
        Number of styles that differ from defaults
    """
    if not styles:
        return 0

    defaults = get_category_defaults(category)
    count = 0

    for style_name, user_value in styles.items():
        if style_name in defaults and user_value != defaults.get(style_name):
            count += 1

    return count


def get_changed_styles_list(category: str, styles: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Get list of styles that differ from category defaults with details.

    Returns list of dicts with style info for UI display.

    Args:
        category: The persona category
        styles: Dictionary of style dimension -> user-selected value

    Returns:
        List of dicts with 'name', 'value', 'default', 'label' for each changed style
    """
    if not styles:
        return []

    defaults = get_category_defaults(category)
    changed = []

    for style_name, user_value in styles.items():
        default_value = defaults.get(style_name)
        if style_name in defaults and user_value != default_value:
            changed.append({
                "name": style_name,
                "value": user_value,
                "default": default_value,
                "label": STYLE_LABELS.get(style_name, {}).get(user_value, user_value),
                "default_label": STYLE_LABELS.get(style_name, {}).get(default_value, default_value),
            })

    return changed


def convert_legacy_slider_value(slider_value: int) -> str:
    """
    Convert legacy 0-10 slider values to 3-level scale.

    Migration helper for existing persona data.

    Args:
        slider_value: Integer 0-10 from old slider

    Returns:
        String value for 3-level scale ("low"/"neutral"/"high" style)
    """
    if slider_value <= 3:
        return "low"  # Will map to first option (cold, casual, gentle, minimal)
    elif slider_value <= 6:
        return "neutral"  # Will map to middle option
    else:
        return "high"  # Will map to third option (warm, formal, direct, playful)


def migrate_legacy_styles(
    legacy_communication_style: Dict[str, int],
    style_mapping: Optional[Dict[str, Dict[str, str]]] = None
) -> Dict[str, str]:
    """
    Convert legacy communication_style (0-10 sliders) to new 3-level format.

    Args:
        legacy_communication_style: Old format with integer values 0-10
        style_mapping: Optional custom mapping from old field names to new

    Returns:
        New format dictionary with 3-level string values
    """
    # Default mapping from old field names to new style dimensions
    default_mapping = {
        # Old field -> (new dimension, value mapping)
        "warmth": ("warmth", {"low": "cold", "neutral": "neutral", "high": "warm"}),
        "empathy": ("warmth", {"low": "cold", "neutral": "neutral", "high": "warm"}),
        "formality": ("formality", {"low": "casual", "neutral": "neutral", "high": "formal"}),
        "directness": ("directness", {"low": "gentle", "neutral": "balanced", "high": "direct"}),
        "assertiveness": ("directness", {"low": "gentle", "neutral": "balanced", "high": "direct"}),
        "humor": ("humor", {"low": "minimal", "neutral": "moderate", "high": "playful"}),
        "playfulness": ("humor", {"low": "minimal", "neutral": "moderate", "high": "playful"}),
    }

    new_styles: Dict[str, str] = {}

    for old_field, old_value in legacy_communication_style.items():
        if old_field not in default_mapping:
            continue

        new_dimension, value_map = default_mapping[old_field]

        # Skip if we already have a value for this dimension
        if new_dimension in new_styles:
            continue

        # Convert 0-10 to 3-level
        level = convert_legacy_slider_value(old_value)
        new_styles[new_dimension] = value_map[level]

    return new_styles


def get_all_style_info() -> Dict[str, Dict]:
    """
    Get complete style configuration info for frontend.

    Returns structure suitable for rendering style controls in UI.
    """
    return {
        "dimensions": list(STYLE_OPTIONS.keys()),
        "options": STYLE_OPTIONS,
        "labels": STYLE_LABELS,
        "descriptions": STYLE_DESCRIPTIONS,
        "category_defaults": CATEGORY_DEFAULTS,
    }
