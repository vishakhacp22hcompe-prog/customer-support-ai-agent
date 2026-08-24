class SourcePolicy:
    """Determines which knowledge-base sources should be trusted."""

    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base

    def classify(self, document_name):
        name = document_name.lower()

        if "legacy" in name:
            return "legacy"

        if "migration" in name:
            return "internal"

        if "current" in name:
            return "current"

        return "standard"

    def rank(self, documents):
        """Prioritize authoritative sources."""

        priority = {
            "current": 4,
            "standard": 3,
            "internal": 2,
            "legacy": 1,
        }

        ranked = []

        for document in documents:
            source_type = self.classify(document["name"])

            item = dict(document)
            item["source_type"] = source_type
            item["authority"] = priority[source_type]

            ranked.append(item)

        ranked.sort(
            key=lambda item: (
                item["authority"],
                item.get("score", 0)
            ),
            reverse=True,
        )

        return ranked

    def trusted_results(self, query, limit=5):
        """Search the knowledge base and prioritize authoritative sources."""

        # Important: our KnowledgeBase.search() currently accepts
        # only the query argument.
        results = self.knowledge_base.search(query)

        ranked = self.rank(results)

        return ranked[:limit]