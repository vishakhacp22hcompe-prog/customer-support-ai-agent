from app.knowledge_base import KnowledgeBase
from app.source_policy import SourcePolicy


def test_current_policy_has_priority_over_legacy():
    kb = KnowledgeBase()
    policy = SourcePolicy(kb)

    results = policy.trusted_results(
        "returns policy 30 days 60 days"
    )

    assert len(results) > 0

    current_results = [
        item for item in results
        if item["source_type"] == "current"
    ]

    assert len(current_results) > 0