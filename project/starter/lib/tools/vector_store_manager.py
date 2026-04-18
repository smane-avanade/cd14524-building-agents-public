import os
import json
import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class QueryResult:
    def __init__(self, documents, distances):
        self.documents = documents
        self.distances = distances


class VectorStoreManager:
    def __init__(
        self,
        collection_name="udaplay",
        db_path="chromadb",
        embedding_model="text-embedding-3-small",
    ):
        self.embedding_model = embedding_model

        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://openai.vocareum.com/v1",
        )

        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name
        )

    def build_game_document(self, game):
        return (
            f"[{game['Platform']}] {game['Name']} "
            f"({game['YearOfRelease']}) - {game['Description']}"
        )

    def embed_text(self, text=[]):
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=[*text]
        )
        return response.data[0].embedding

    def index_game(self, game, doc_id):
        content = self.build_game_document(game)
        embedding = self.embed_text(content)

        self.collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[game],
            embeddings=[embedding],
        )

    def index_games_from_folder(self, data_dir="games"):
        for file_name in sorted(os.listdir(data_dir)):
            if not file_name.endswith(".json"):
                continue

            file_path = os.path.join(data_dir, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                game = json.load(f)

            doc_id = os.path.splitext(file_name)[0]
            self.index_game(game, doc_id)
            print(f"Indexed {doc_id}: {game['Name']}")

    def search_collection(self, query = [], n_results=5):
        query_embedding = self.embed_text([*query])
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

    def search_games(self, query_texts=[], n_results=5):
        results = self.search_collection([*query_texts], n_results=n_results)

        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        formatted_results = []
        for i, doc_id in enumerate(ids):
            formatted_results.append({
                "id": doc_id,
                "document": docs[i] if i < len(docs) else None,
                "metadata": metas[i] if i < len(metas) else None,
                "distance": distances[i] if i < len(distances) else None,
            })

        return formatted_results

    def search_games_tool(self, query=[], n_results=5):
        results = self.search_games(query, n_results=n_results)

        if not results:
            return "No matching games found."

        lines = []
        for i, result in enumerate(results, 1):
            metadata = result.get("metadata") or {}
            name = metadata.get("Name", "Unknown")
            platform = metadata.get("Platform", "Unknown")
            year = metadata.get("YearOfRelease", "Unknown")
            distance = result.get("distance", "N/A")
            document = result.get("document", "")

            lines.append(
                f"{i}. {name} ({year}) on {platform} | distance={distance}\n"
                f"   {document}"
            )

        return "\n\n".join(lines)

    def query(self, query_texts=[], n_results=5):
        results = self.search_games(query_texts, n_results=n_results)

        if not results:
            return []

        documents=[]
        distances=[]
        metadatas=[]

        for result in results:
            distance = result.get("distance", "N/A")
            document = result.get("document", "")
            metadata = result.get("metadata", {})

            documents.append(document)
            distances.append(distance)
            metadatas.append(metadata)

        return dict(
            documents=[documents],
            distances=[distances],
            metadata=[metadatas]
        )

    def test(self, args=None):
        print(f'OK Tested: %s' % (args))

