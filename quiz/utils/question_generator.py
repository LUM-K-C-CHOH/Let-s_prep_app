import re
import random
import textwrap

# A tiny stopword list so fill-blanks pick better words
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to",
    "for", "with", "by", "is", "are", "was", "were", "be", "been",
    "it", "this", "that", "these", "those", "as", "from", "you", "your",
    "their", "they", "we", "our", "i"
}


def split_into_sentences(text):
    # simple sentence splitter
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def clean_sentence(sentence):
    # collapse spaces, strip weird line breaks
    sentence = sentence.replace("\n", " ")
    sentence = re.sub(r"\s+", " ", sentence)
    return sentence.strip()


def important_words(sentence):
    """Return a list of 'important' words = not stopwords, medium length."""
    words = []
    for raw in sentence.split():
        w = re.sub(r"[^\w\-]", "", raw)  # remove punctuation
        if len(w) >= 4 and w.lower() not in STOPWORDS:
            words.append(w)
    # keep unique order
    seen = set()
    cleaned = []
    for w in words:
        low = w.lower()
        if low not in seen:
            seen.add(low)
            cleaned.append(w)
    return cleaned


def generate_questions(text, question_type, num_questions=10):
    """
    Main entry. Returns a list of question dicts.

    Each dict has keys:
      type, prompt, option_a..d, correct_option, answer_text, explanation
    """
    sentences = [clean_sentence(s) for s in split_into_sentences(text)]
    if not sentences:
        return []

    # Limit to first 200 sentences to avoid blowing up
    sentences = sentences[:200]

    questions = []

    for sentence in sentences:
        if len(questions) >= num_questions:
            break

        if question_type == "mcq":
            q = make_mcq(sentence, sentences)
        elif question_type == "flashcard":
            q = make_flashcard(sentence)
        elif question_type == "fill_blank":
            q = make_fill_blank(sentence)
        elif question_type == "short_answer":
            q = make_short_answer(sentence)
        else:
            # default fallback: short answer
            q = make_short_answer(sentence)

        if q:
            questions.append(q)

    # if we somehow have fewer than requested, just return what we have
    return questions


# ---------- Question type builders ----------

def make_flashcard(sentence):
    """
    Flashcard: front = question, back = key idea (here: the sentence itself).
    """
    if len(sentence.split()) < 4:
        return None

    prompt = "What is the key idea of this sentence?"
    answer = sentence

    return {
        "type": "flashcard",
        "prompt": prompt + "\n\n" + wrap(answer),
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct_option": "",
        "answer_text": answer,
        "explanation": "",
    }


def make_fill_blank(sentence):
    """
    Replace one important word with _____ and use removed word as answer.
    """
    words = sentence.split()
    if len(words) < 6:
        return None

    candidates = important_words(sentence)
    if not candidates:
        return None

    target = random.choice(candidates)

    new_words = []
    replaced = False
    for w in words:
        stripped = re.sub(r"[^\w\-]", "", w)
        if not replaced and stripped.lower() == target.lower():
            # keep punctuation after the blank, if any
            suffix = ""
            if w.endswith((".", ",", "?", "!", ";", ":")):
                suffix = w[-1]
            new_words.append("_____" + suffix)
            replaced = True
        else:
            new_words.append(w)

    if not replaced:
        return None

    prompt = "Fill in the blank:\n\n" + " ".join(new_words)
    answer = target

    return {
        "type": "fill_blank",
        "prompt": wrap(prompt),
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct_option": "",
        "answer_text": answer,
        "explanation": f"The missing word is '{answer}'.",
    }


def make_mcq(sentence, all_sentences):
    """
    MCQ: ask which word is in the sentence.
    Correct answer = one real word, distractors = words from other sentences.
    """
    real_words = important_words(sentence)
    if len(real_words) < 1:
        return None

    correct = random.choice(real_words)

    # get distractors from other sentences
    pool = []
    for s in all_sentences:
        if s == sentence:
            continue
        pool.extend(important_words(s))

    random.shuffle(pool)
    distractors = []
    seen = {correct.lower()}

    for w in pool:
        low = w.lower()
        if low not in seen:
            distractors.append(w)
            seen.add(low)
        if len(distractors) >= 3:
            break

    # Not enough distractors? bail
    if len(distractors) < 3:
        return None

    options = [correct] + distractors
    random.shuffle(options)

    # find index of correct
    correct_index = options.index(correct)
    letter_map = ["A", "B", "C", "D"]
    correct_letter = letter_map[correct_index]

    prompt = f"Which of these words appears in this sentence?\n\n\"{wrap(sentence)}\""

    return {
        "type": "mcq",
        "prompt": prompt,
        "option_a": options[0],
        "option_b": options[1],
        "option_c": options[2],
        "option_d": options[3],
        "correct_option": correct_letter,
        "answer_text": correct,
        "explanation": f"'{correct}' is present in the sentence.",
    }


def make_short_answer(sentence):
    """
    Short answer: ask learner to explain sentence in their own words.
    """
    if len(sentence.split()) < 4:
        return None

    prompt = "In your own words, what does this sentence mean?\n\n" + wrap(sentence)

    return {
        "type": "short_answer",
        "prompt": prompt,
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct_option": "",
        "answer_text": "",
        "explanation": "",
    }


def wrap(text, width=80):
    """Nice wrapping for long sentences."""
    return "\n".join(textwrap.wrap(text, width=width))