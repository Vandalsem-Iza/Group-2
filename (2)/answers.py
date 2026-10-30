"""The answer pool and input validation, independent of the window."""
from dataclasses import dataclass
import random
import re


ANSWERS = (
    "without a doubt.",
    "outlook good.",
    "signs point to yes",
    "it is certain.",
    "Definitely.",
    "Concentrate and ask again.",
    "My sources say no.",
    "Don't count on it.",
    "Very doubtful.",
    "absolutly not.",
    "No.",
)


@dataclass(frozen=True)
class Reading:
    name: str
    question: str
    answer: str

    @property
    def answer_type(self) -> str:
        index = ANSWERS.index(self.answer)
        return "yes" if index < 5 else "maybe" if index == 5 else "no"


def normalize_inputs(name: str, question: str) -> tuple[str, str]:
    """A name is optional; a nonempty question is required."""
    name = " ".join(name.split())
    question = " ".join(question.split())
    if len(name) > 60:
        raise ValueError("Please keep your name to 60 characters or fewer.")
    if not question:
        raise ValueError("Please type a question first.")
    if len(question) > 300:
        raise ValueError("Please keep your question to 300 characters or fewer.")
    return name, question


def question_hint(question: str) -> str:
    """Offer a gentle nudge rather than blocking unusual questions."""
    if re.match(r"^(what|why|how)\b", question, re.IGNORECASE):
        return "Try a yes-or-no question. Click Ask again to use this one anyway."
    if not question.endswith("?"):
        return "Questions usually end with '?'. Add it, or click Ask again to continue."
    return ""


def ask_ball(name: str, question: str) -> Reading:
    """Select one of the 11 responses copied verbatim from magic8code.ipynb."""
    name, question = normalize_inputs(name, question)
    return Reading(name, question, random.choice(ANSWERS))
