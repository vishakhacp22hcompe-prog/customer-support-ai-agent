from pathlib import Path


class KnowledgeBase:
    """Loads support documents from the local knowledge base."""

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
            })

        return documents

    def all_documents(self):
        return list(self.documents)

    def search(self, query):
        """
        Simple local keyword retrieval.

        We will improve the ranking logic later.
        """
        terms = {
            word.lower()
            for word in query.split()
            if len(word) > 2
        }

        matches = []

        for document in self.documents:
            content = document["content"].lower()

            score = sum(
                1 for term in terms
                if term in content
            )

            if score > 0:
                matches.append({
                    "name": document["name"],
                    "content": document["content"],
                    "score": score,
                })

        matches.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return matches