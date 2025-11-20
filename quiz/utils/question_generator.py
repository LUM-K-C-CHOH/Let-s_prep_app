import os
import json
import random
import textwrap

try:
    # New OpenAI client, from openai>=1.x
    from openai import OpenAI

    # Set a *short* timeout so we error in Python instead of letting gunicorn kill the worker
    _openai_client = OpenAI(timeout=15.0)  # 15 seconds total per request
except ImportError:
    _openai_client = None
# ============ HELPERS ============

def _clean_text(text: str, max_len: int = 8000) -> str:
    """Basic cleanup + truncate so we don't send giant files to the model."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text


def _split_sentences(text: str):
    """
    Rough sentence splitter that respects '.', '!' and '?'.
    Keeps only non-empty trimmed chunks.
    """
    if not text:
        return []

    # unify newlines to spaces
    text = text.replace("\n", " ")
    temp = []
    current = []

    for ch in text:
        current.append(ch)
        if ch in ".!?":
            temp.append("".join(current))
            current = []
    if current:
        temp.append("".join(current))

    sentences = [s.strip() for s in temp if s.strip()]
    return sentences


def _pick_content_word(words):
    """Pick a 'content' word (not the, and, etc.) or fall back to last word."""
    stopwords = {"the", "and", "of", "a", "an", "to", "in", "on", "for", "is", "are"}
    content = [w for w in words if w.lower().strip(",.") not in stopwords]
    if content:
        return random.choice(content)
    return words[-1]


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

    # Default to True so Render + local behave the same unless overridden.
    use_ai = getattr(settings, "USE_AI_QUESTIONS", True)
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    model_name = getattr(settings, "AI_MODEL_NAME", "gpt-4o-mini")

    # Normalize question_type used in our logic
    question_type = question_type or "mcq"
    if question_type not in {"mcq", "flashcard", "fill_blank", "short_answer"}:
        question_type = "mcq"

    if use_ai and _openai_client is not None and has_key and text:
        print(">>> LETS_PREP: Using AI question generator.")
        try:
            return generate_questions_ai(text, question_type, num_questions, model_name)
        except Exception as e:
            # Log + fall back
            print(">>> LETS_PREP: AI generation failed, falling back to SIMPLE mode:", e)

    print(">>> LETS_PREP: Using SIMPLE (offline) question generator.")
    return generate_questions_simple(text, question_type, num_questions)


# ============ SIMPLE OFFLINE GENERATOR ============

def generate_questions_simple(text: str, question_type: str, num_questions: int):
    """
    Heuristic generator, used if AI is disabled or fails.
    Tries to still make questions that relate to the notes.

    IMPORTANT: will only generate the requested question_type
    (no mixing MCQ + flashcards anymore).
    """
    sentences = _split_sentences(text)
    if not sentences:
        sentences = ["This is a placeholder sentence because no text was found."]

    questions = []
    n_sent = len(sentences)

    for i in range(num_questions):
        base = sentences[i % n_sent]
        words = base.split()

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

        # ---------- FLASHCARDS ----------
        if question_type == "flashcard":
            # Try to infer term + definition from patterns like "Term – definition" or "Term: definition"
            term = None
            definition = None

            if " - " in base:
                parts = base.split(" - ", 1)
                term, definition = parts[0].strip(), parts[1].strip()
            elif " – " in base:
                parts = base.split(" – ", 1)
                term, definition = parts[0].strip(), parts[1].strip()
            elif ":" in base and len(base.split(":")[0].split()) <= 5:
                parts = base.split(":", 1)
                term, definition = parts[0].strip(), parts[1].strip()
            else:
                # Fallback: treat first 3–5 words as a term-ish phrase
                term = " ".join(words[: min(len(words), 5)])
                definition = base

            q["prompt"] = term
            q["answer_text"] = definition
            q["explanation"] = definition

        # ---------- MCQ ----------
        elif question_type == "mcq":
            # Try to split into stem + key idea for option A
            if len(words) > 10:
                split_idx = len(words) // 2
                stem = " ".join(words[:split_idx])
                concept = " ".join(words[split_idx:])
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
            q["explanation"] = "Option A is closest to the wording and meaning in the notes."

        # ---------- FILL-IN-THE-BLANK ----------
        elif question_type == "fill_blank":
            if len(words) > 4:
                hidden = _pick_content_word(words)
                prompt_words = []
                hidden_done = False
                for w in words:
                    if not hidden_done and w == hidden:
                        prompt_words.append("_____")
                        hidden_done = True
                    else:
                        prompt_words.append(w)
                prompt = " ".join(prompt_words)
                q["prompt"] = f"Fill in the missing word or phrase:\n\n{prompt}"
                q["answer_text"] = hidden.strip(",.")
                q["explanation"] = f"The missing word from the original notes is '{hidden.strip(',.')}'."
            else:
                q["prompt"] = base
                q["answer_text"] = base
                q["explanation"] = "Short sentence used directly as the answer."

        # ---------- SHORT ANSWER ----------
        elif question_type == "short_answer":
            # Use the first few words as a "topic" and ask to explain
            topic = " ".join(words[: min(len(words), 7)])
            q["prompt"] = f"Briefly explain this idea from your notes:\n\n{topic}"
            q["answer_text"] = base
            q["explanation"] = "A good answer should capture the main idea of the original sentence."

        # Fallback (shouldn't normally hit)
        else:
            q["type"] = "short_answer"
            q["prompt"] = base
            q["answer_text"] = base
            q["explanation"] = "This question was generated from a single sentence in your notes."

        questions.append(q)

    return questions


# ============ AI-POWERED GENERATOR ============

def generate_questions_ai(text: str, question_type: str, num_questions: int, model_name: str):
    """
    Use OpenAI Responses API to generate a list of question dicts.

    We ask the model to return a JSON list with fields matching our Question model.
    We also *force* all questions to use the requested question_type,
    so MCQ won't be mixed with flashcards, etc.
    """
    if not text:
        raise ValueError("No text provided to AI question generator.")

    # Use a trimmed portion of the text (already cleaned earlier)
    snippet = textwrap.shorten(text, width=3000, placeholder="...")

    # Label (for the prompt) and normalized type
    if question_type == "mcq":
        qt_label = "multiple-choice questions"
        qt_exact = "mcq"
    elif question_type == "flashcard":
        qt_label = "flashcards (term on front, explanation on back)"
        qt_exact = "flashcard"
    elif question_type == "fill_blank":
        qt_label = "fill-in-the-blank questions"
        qt_exact = "fill_blank"
    else:
        qt_label = "short-answer questions"
        qt_exact = "short_answer"

    system_instructions = (
        "You are an assistant that creates high quality study questions from course notes. "
        "Generate clear, concise questions appropriate for college-level studying. "
        "Stay strictly grounded in the notes provided. Do not invent new facts."
    )

    user_prompt = f"""
You are given course notes. Generate exactly {num_questions} high-quality {qt_label}
that directly test understanding of the ideas in the notes.

ALL QUESTIONS MUST BE OF TYPE: "{qt_exact}" ONLY.
Do not mix question types. Every object in the JSON list must have "type" set to "{qt_exact}".

Guidelines:
- Base EVERY question ONLY on the text below. Do NOT invent facts that are not present.
- Focus on key concepts, definitions, processes, comparisons, and cause-effect.
- For "mcq":
    - Ask about one clear idea.
    - Provide 1 correct option and 3 plausible but wrong distractors.
    - Distractors must be related to the topic but clearly incorrect.
- For "flashcard":
    - Put a short term/phrase on the front ("prompt").
    - Put the explanation/definition in "answer_text".
- For "fill_blank":
    - Use a sentence from the notes.
    - Replace one important word or short phrase with "_____".
    - Put the hidden word/phrase in "answer_text".
- For "short_answer":
    - Ask a direct question that can be answered in 1–3 sentences.
    - Put the ideal short answer in "answer_text".

Return STRICT JSON ONLY, no commentary, no markdown code fences.
The JSON must be a list of question objects.
Each object must have:
- "type": exactly "{qt_exact}"
- "prompt": the question text for the student
- "option_a", "option_b", "option_c", "option_d": strings
    - For non-MCQ types, leave these as empty strings.
- "correct_option": "A" | "B" | "C" | "D"
    - For non-MCQ types, leave this as an empty string.
- "answer_text": the correct answer
- "explanation": a brief explanation of why the answer is correct (or helpful extra context).

NOTES (SOURCE MATERIAL):
{snippet}
"""

    response = _openai_client.responses.create(
        model=model_name,
        instructions=system_instructions,
        input=user_prompt,
        max_output_tokens=900,
    )

    # SDK convenience property to get the concatenated text
    raw_output = response.output_text  # type: ignore[attr-defined]

    # ---------- CLEAN THE RAW OUTPUT ----------
    text = raw_output.strip()

    # Strip markdown code fences like ```json ... ``` if the model added them
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
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
        # Let the caller fall back to simple mode
        raise e

    questions = []
    for item in data:
        # Force type to be the requested one, even if the model got creative.
        item_type = item.get("type", qt_exact)
        if item_type not in {"mcq", "flashcard", "fill_blank", "short_answer"}:
            item_type = qt_exact

        q = {
            "type": item_type,
            "prompt": item.get("prompt", "").strip(),
            "option_a": item.get("option_a", "") or "",
            "option_b": item.get("option_b", "") or "",
            "option_c": item.get("option_c", "") or "",
            "option_d": item.get("option_d", "") or "",
            "correct_option": item.get("correct_option", "") or "",
            "answer_text": item.get("answer_text", "").strip(),
            "explanation": item.get("explanation", "").strip(),
        }

        # Non-MCQ types should not carry random options/correct_option
        if item_type != "mcq":
            q["option_a"] = ""
            q["option_b"] = ""
            q["option_c"] = ""
            q["option_d"] = ""
            q["correct_option"] = ""

        questions.append(q)

    return questions