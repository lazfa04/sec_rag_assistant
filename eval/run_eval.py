import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retrieval.answerer import answer_question

QUESTIONS_PATH = Path(__file__).with_name("questions.json")
SEPARATOR = "=" * 80


def _retrieved_sections(sources: list[dict]) -> str:
    if not sources:
        return "  (none)"
    lines = []
    for i, source in enumerate(sources, start=1):
        item = source.get("item_number", "?")
        title = source.get("item_title", "")
        ticker = source.get("ticker", "")
        filing_date = source.get("filing_date", "")
        similarity = source.get("similarity")
        score = f"  similarity={similarity:.3f}" if isinstance(similarity, (int, float)) else ""
        lines.append(
            f"  [{i}] Item {item} {title} ({ticker}, {filing_date}){score}"
        )
    return "\n".join(lines)


def run_eval() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    total = len(questions)
    print(f"Running {total} eval questions (manual review — no auto-grade)\n")

    for i, item in enumerate(questions, start=1):
        question = item["question"]
        result = answer_question(question)
        print(SEPARATOR)
        print(f"[{i}/{total}]")
        print("Question:")
        print(f"  {question}")
        print()
        print("Generated answer:")
        print(f"  {result.get('answer', '').strip()}")
        print()
        print("Expected answer:")
        print(f"  {item.get('expected_answer', '')}")
        print()
        print(f"Expected section: {item.get('expected_section', '')}")
        print("Retrieved sections:")
        print(_retrieved_sections(result.get("sources") or []))
        print()


if __name__ == "__main__":
    run_eval()
