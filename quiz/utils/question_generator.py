import os
import json
import random
import textwrap

try:
    # New OpenAI client, from openai>=1.x
    from openai import OpenAI
    _openai_client = OpenAI()
except ImportError:
    _openai_client = None


def _clean_text(text: str, max_len: int = 8000) -> str:
    """Basic cleanup + truncate so we don't send giant files to the model."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text


# ============ PUBLIC ENTRY POINT ============

def generate_questions(text: str, question_type: str, num_questions: int):
    """
    Main function used by views.py.

    - If AI is enabled + configured, use the AI generator.
    - Otherwise, fall back to the simple rule-based generator.
    """
    from django.conf import settings  # imported lazily to avoid issues at import time

    text = _clean_text(text)
    num_questions = max(1, int(num_questions))

    use_ai = getattr(settings, "USE_AI_QUESTIONS", False)
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    model_name = getattr(settings, "AI_MODEL_NAME", "gpt-4o-mini")

    if use_ai and _openai_client is not None and has_key:
        print(">>> LETS_PREP: Using AI question generator.")
        try:
            return generate_questions_ai(text, question_type, num_questions, model_name)
        except Exception as e:
            # Log + fall back
            print(">>> LETS_PREP: AI generation failed, falling back to SIMPLE mode:", e)

    print(">>> LETS_PREP: Using SIMPLE (offline) question generator.")
    # Fallback: simple offline generator
    return generate_questions_simple(text, question_type, num_questions)


# ============ SIMPLE OFFLINE GENERATOR ============

def generate_questions_simple(text: str, question_type: str, num_questions: int):
    """
    Basic heuristic generator, used if AI is disabled or fails.
    Tries to still make questions that relate to the notes.
    """
    # Split into rough "sentences"
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    if not sentences:
        sentences = ["This is a placeholder sentence because no text was found."]

    questions = []

    for i in range(num_questions):
        base = sentences[i % len(sentences)]
        q = {
            "type": question_type,
            "prompt": "",
            "option_a": "",
            "option_b": "",
            "option_c": "",
            "option_d": "",
            "correct_option": "",
            "answer_text": "",
            "explanation": "",
        }

        if question_type == "flashcard":
            # Treat the sentence as an explanation and ask for the key idea
            q["prompt"] = f"What is the key idea in this statement?\n\n{base}"
            q["answer_text"] = base

        elif question_type == "mcq":
            # Try to separate a "stem" and a "concept" from the sentence
            words = base.split()
            if len(words) > 10:
                stem = " ".join(words[: len(words) // 2])
                concept = " ".join(words[len(words) // 2 :])
            else:
                stem = base
                concept = base

            q["prompt"] = (
                "According to your notes, which statement best matches this idea?\n\n"
                f"{stem}"
            )
            q["option_a"] = concept
            q["option_b"] = "A detail that does not fully match the notes."
            q["option_c"] = "A statement that contradicts the notes."
            q["option_d"] = "An unrelated concept."
            q["correct_option"] = "A"
            q["answer_text"] = concept
            q["explanation"] = (
                "Option A is closest to the wording and meaning in the notes."
            )

        elif question_type in ("fill_blank", "short_answer"):
            words = base.split()
            if len(words) > 4:
                # Hide an important-looking word (not 'the', 'and', etc.)
                content_words = [
                    w for w in words if w.lower() not in ("the", "and", "of", "a", "an")
                ]
                if content_words:
                    hidden = random.choice(content_words)
                else:
                    hidden = words[-1]

                prompt_words = []
                hidden_done = False
                for w in words:
                    if not hidden_done and w == hidden:
                        prompt_words.append("_____")
                        hidden_done = True
                    else:
                        prompt_words.append(w)
                prompt = " ".join(prompt_words)
                q["prompt"] = f"Fill in the missing word:\n\n{prompt}"
                q["answer_text"] = hidden
            else:
                q["prompt"] = base
                q["answer_text"] = base

            if question_type == "short_answer":
                q["type"] = "short_answer"

        else:
            # default to short answer
            q["type"] = "short_answer"
            q["prompt"] = base
            q["answer_text"] = base

        questions.append(q)

    return questions


# ============ AI-POWERED GENERATOR ============

def generate_questions_ai(text: str, question_type: str, num_questions: int, model_name: str):
    """
    Use OpenAI Responses API to generate a list of question dicts.

    We ask the model to return a JSON list with fields matching our Question model.
    """
    if not text:
        raise ValueError("No text provided to AI question generator.")

    # Use a trimmed portion of the text (already cleaned earlier)
    snippet = textwrap.shorten(text, width=6000, placeholder="...")

    # Normalize question_type for the prompt
    if question_type == "mcq":
        qt_label = "multiple-choice questions"
    elif question_type == "flashcard":
        qt_label = "flashcards (term + explanation)"
    elif question_type in ("fill_blank", "fill-in", "fill"):
        qt_label = "fill-in-the-blank items"
        question_type = "fill_blank"
    else:
        qt_label = "short-answer questions"
        question_type = "short_answer"

    system_instructions = (
        "You are an assistant that creates high quality study questions from course notes. "
        "Generate clear, concise questions appropriate for college-level studying."
    )

    user_prompt = f"""
You are given study notes. Generate {num_questions} high-quality {qt_label}
that directly test understanding of the ideas in the notes.

Use this main question style: "{question_type}" but you may vary exact wording
to make questions clear.

Rules:
- Base EVERY question ONLY on the text below. Do NOT invent facts that are not present.
- Focus on key concepts, definitions, processes, comparisons, and cause-effect.
- For MCQ: provide 1 correct option and 3 plausible but wrong distractors.
- For flashcards: use a short term/phrase on the front and a clear explanation on the back.
- For fill-in-the-blank: hide an important word or short phrase from a sentence.
- For short-answer: ask direct questions answerable in 1–3 sentences.
- Keep language clear and student-friendly.

Return STRICT JSON ONLY, no commentary. The JSON must be a list of question objects.
Each object must have:
- "type": "mcq" | "flashcard" | "fill_blank" | "short_answer"
- "prompt": the question text
- "option_a", "option_b", "option_c", "option_d": strings (empty if not MCQ)
- "correct_option": "A" | "B" | "C" | "D" (empty if not MCQ)
- "answer_text": the correct answer (for flashcards / fill-in / short answers)
- "explanation": a short explanation of why the answer is correct

NOTES:
{snippet}
"""

    response = _openai_client.responses.create(
        model=model_name,
        instructions=system_instructions,
        input=user_prompt,
        max_output_tokens=2048,
    )

    # SDK convenience property to get the concatenated text
    raw_output = response.output_text  # type: ignore[attr-defined]
    # print a tiny preview if you want:
    # print(">>> LETS_PREP: Raw AI output preview:", raw_output[:200])

    # ---------- CLEAN THE RAW OUTPUT ----------
    text = raw_output.strip()

    # Strip markdown code fences like ```json ... ```
    if text.startswith("```"):
        # drop the first line (```json or ```)
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        # drop trailing ```
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].strip()

    # Keep only the JSON array region [ ... ]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    # Now parse JSON
    try:
        data = json.loads(text)
    except Exception as e:
        print(">>> LETS_PREP: JSON parse failed AFTER cleaning. Text preview:")
        print(text[:2000])
        raise e

    questions = []
    for item in data:
        q = {
            "type": item.get("type", question_type),
            "prompt": item.get("prompt", ""),
            "option_a": item.get("option_a", ""),
            "option_b": item.get("option_b", ""),
            "option_c": item.get("option_c", ""),
            "option_d": item.get("option_d", ""),
            "correct_option": item.get("correct_option", ""),
            "answer_text": item.get("answer_text", ""),
            "explanation": item.get("explanation", ""),
        }
        questions.append(q)

    return questions