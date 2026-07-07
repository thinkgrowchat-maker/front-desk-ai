"""
Quick, deterministic check of the retrieval layer — no API key required.

Run:  python3 test_retrieval.py
"""

from knowledge_base import KNOWLEDGE_BASE
from retrieval import build_index, search

CASES = [
    ("What time do you close on Sunday?", "hours"),
    ("where can I park my car", "parking"),
    ("can I bring my dog to dinner", "pets"),
    ("do you have anything vegan", "dietary"),
    ("I want to book the place for a wedding", "private-events"),
    ("do you take apple pay", "payment"),
    ("is it wheelchair accessible", "accessibility"),
    ("can I get it delivered", "takeout"),
]


def main():
    index = build_index(KNOWLEDGE_BASE)
    passed = 0
    print(f"\nRetrieval test — {len(KNOWLEDGE_BASE)} KB entries\n" + "-" * 52)
    for query, expected in CASES:
        hits = search(index, query, top_k=3)
        top = hits[0]["doc"]["id"] if hits else None
        ok = top == expected
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {query!r}")
        for h in hits:
            print(f"        {h['score']:.3f}  {h['doc']['id']}")
    print("-" * 52)
    print(f"{passed}/{len(CASES)} cases matched the expected top result\n")


if __name__ == "__main__":
    main()
