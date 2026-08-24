from pathlib import Path
import re


class KnowledgeBase:
    """Local searchable store for customer-support documents."""

    def __init__(self, folder=None):
        self.folder = (
            Path(folder)
            if folder
            else Path(__file__).resolve().parent.parent / "knowledge-base"
        )

        self.documents = self._load_documents()

    def _load_documents(self):
        documents = []

        for path in sorted(self.folder.glob("*.md")):
            text = path.read_text(encoding="utf-8")

            documents.append({
                "name": path.name,
                "content": text,
                "tokens": self._tokenize(text),
            })

        return documents

    @staticmethod
    def _tokenize(text):
        return set(
            re.findall(r"[a-z0-9]+", text.lower())
        )

    @staticmethod
    def _query_terms(query):
        return set(
            re.findall(r"[a-z0-9]+", query.lower())
        )

    def all_documents(self):
        return list(self.documents)

    def search(self, query, limit=5):
        """Return the most relevant documents for a customer question."""

        query_terms = self._query_terms(query)

        if not query_terms:
            return []

        ranked = []

        for document in self.documents:
            overlap = query_terms & document["tokens"]

            if not overlap:
                continue

            score = len(overlap)

            # Give extra weight to exact phrases appearing in the document.
            normalized_query = " ".join(query.lower().split())
            normalized_content = " ".join(
                document["content"].lower().split()
            )

            if normalized_query in normalized_content:
                score += 5

            ranked.append({
                "name": document["name"],
                "content": document["content"],
                "score": score,
                "matched_terms": sorted(overlap),
            })

        ranked.sort(
            key=lambda item: (
                item["score"],
                len(item["matched_terms"])
            ),
            reverse=True,
        )

        return ranked[:limit]