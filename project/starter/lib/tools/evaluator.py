import json
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class Evaluator:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, api_key: Optional[str] = None):
        self.model = model
        self.temperature = temperature
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def _normalize_retrieved_docs(self, retrieved_docs: Any) -> List[Dict[str, Any]]:
        if retrieved_docs is None:
            return []

        if isinstance(retrieved_docs, dict):
            documents = retrieved_docs.get("documents", [])
            distances = retrieved_docs.get("distances", [])
            metadatas = retrieved_docs.get("metadata", []) or retrieved_docs.get("metadatas", [])

            if documents and isinstance(documents[0], list):
                documents = documents[0]
            if distances and isinstance(distances[0], list):
                distances = distances[0]
            if metadatas and isinstance(metadatas[0], list):
                metadatas = metadatas[0]

            normalized = []
            for index, document_text in enumerate(documents):
                normalized.append({
                    "document": document_text,
                    "distance": distances[index] if index < len(distances) else None,
                    "metadata": metadatas[index] if index < len(metadatas) else None,
                })
            return normalized

        if isinstance(retrieved_docs, list):
            if all(isinstance(item, dict) for item in retrieved_docs):
                return retrieved_docs
            return [{"document": str(item), "distance": None, "metadata": None} for item in retrieved_docs]

        return [{"document": str(retrieved_docs), "distance": None, "metadata": None}]

    def _build_prompt(self, question: str, docs: List[Dict[str, Any]]) -> str:
        doc_lines = []
        for idx, doc in enumerate(docs, start=1):
            metadata = doc.get("metadata") or {}
            name = metadata.get("Name", metadata.get("name", "Unknown"))
            platform = metadata.get("Platform", metadata.get("platform", "Unknown"))
            year = metadata.get("YearOfRelease", metadata.get("year", "Unknown"))
            description = metadata.get("Description", doc.get("document", ""))
            source_text = doc.get("document", "")
            distance = doc.get("distance", "N/A")

            doc_lines.append(
                f"Document {idx}:\n"
                f"  Name: {name}\n"
                f"  Platform: {platform}\n"
                f"  YearOfRelease: {year}\n"
                f"  Description: {description}\n"
                f"  Source text: {source_text}\n"
                f"  Distance: {distance}\n"
            )

        docs_section = "\n".join(doc_lines)

        return (
            "You are a retrieval evaluator.\n"
            "Based on the user's question and the list of retrieved documents, determine whether the documents are useful to answer the question.\n"
            "Return a JSON object with exactly two fields: useful, and description.\n"
            "Do not return any additional text outside of valid JSON.\n\n"
            f"Question: {question}\n\n"
            "Retrieved documents:\n"
            f"{docs_section}\n"
            "Evaluation output format example:\n"
            "{\"useful\": true, \"description\": \"The retrieved documents provide relevant game details for the question.\"}\n"
        )

    def evaluate(self, query_texts: List[str] = [], retrieved_docs: Any = None, n_results: int = 5) -> Dict[str, Any]:
        question = query_texts[0] if isinstance(query_texts, list) else ""
        docs = self._normalize_retrieved_docs(retrieved_docs)
        docs = docs[:n_results]

        if not docs:
            print('Query was empty, ending evaluation with useful=False')
            return {
                "useful": False,
                "description": "No documents were retrieved to evaluate."
            }

        prompt = self._build_prompt(question, docs)

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": "You are an evaluator for search results."},
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message.content.strip()
        try:
            parsed = json.loads(content)
            useful = bool(parsed.get("useful", False))
            description = str(parsed.get("description", "No description provided."))
        except json.JSONDecodeError:
            useful = False
            description = (
                "LLM output could not be parsed as JSON. "
                "Please check that the evaluator response is valid JSON with fields useful and description."
            )

        return {
            "useful": useful,
            "description": description.strip()
        }
