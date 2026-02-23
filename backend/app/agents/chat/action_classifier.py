import json
from app.services.ai_service import AIService
from app.core.logger import get_logger

logger = get_logger(__name__)

# Actions offered when student successfully completes a problem
SUCCESS_ACTIONS = [
    {"id": "practice", "label": "Practice a similar problem", "icon": "pencil"},
    {"id": "quiz", "label": "Quiz me on this topic", "icon": "help-circle"},
    {"id": "explain", "label": "Explain the concept deeper", "icon": "book-open"},
]


async def classify_response_actions(ai_response: str, intent: str) -> list:
    """
    Lightweight classifier: determines if the tutor confirmed the student
    solved a problem correctly. If so, returns suggested action buttons.
    
    Uses a fast LLM call with low token output to keep latency minimal.
    """
    # Only check for canvas review responses — other intents don't need actions
    if intent not in ("canvas_review_request", "hint_request"):
        return []

    ai = AIService()

    prompt = f"""Read this AI tutor response and answer ONE question:
Did the tutor confirm that the student's answer is CORRECT and the problem is COMPLETE?

Rules:
- "Yes" ONLY if the tutor explicitly says the answer is correct/right/spot on/well done
- "No" if the tutor found errors, gave hints, or the problem is still in progress
- "No" if the tutor is explaining a concept without confirming a correct answer

Tutor response:
\"\"\"{ai_response[:1000]}\"\"\"

Respond with ONLY valid JSON: {{"problem_completed": true/false}}"""

    try:
        response = await ai.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            model="gpt-4.1-nano"
        )

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = json.loads(raw)
        if result.get("problem_completed", False):
            logger.info("Problem completed successfully — offering actions")
            return SUCCESS_ACTIONS
        else:
            logger.info("Problem not yet completed — no actions")
            return []
    except Exception as e:
        logger.error(f"Action classifier failed: {e}")
        return []
