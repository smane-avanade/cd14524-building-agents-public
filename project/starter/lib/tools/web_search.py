
import os
from dotenv import load_dotenv
from tavily import TavilyClient
import json


load_dotenv()

client = TavilyClient(os.getenv("TAVILY_API_KEY"))

class WebSearchTool:
    def __init__(self):
        self.name = "web_search"
        self.description = "A tool to search the web for information relevant to a question. Use this tool when you need to find up-to-date information or specific details that may not be in your training data."


    def search(self, query=""):
        response = client.search(query=query)
        print(json.dumps(response, indent=2))
