import os
from typing import List, Dict, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from qdrant_client import QdrantClient
from database.manager import DatabaseManager
from agent.tools import bs_to_ad
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# State definition
class AgentState(TypedDict):
    question: str
    retrieved_docs: List[Dict]
    reasoning_steps: List[str]
    final_answer: str

# Database and LLM Setup
db_manager = DatabaseManager()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash") # Use 2.0 check

# Node 1: Retriever
def retriever_node(state: AgentState):
    question = state["question"]
    # 1. Embed question (in real use, use embedding_manager)
    embedding = db_manager.embedding_manager.get_embedding(question)
    
    # 2. Query Qdrant
    try:
        if hasattr(db_manager.qdrant_client, "search"):
            results = db_manager.qdrant_client.search(
                collection_name=db_manager.collection_name,
                query_vector=embedding,
                limit=3
            )
        else:
            # Fallback to newer API if search is missing for some reason
            results = db_manager.qdrant_client.query_points(
                collection_name=db_manager.collection_name,
                query=embedding,
                limit=3
            ).points
    except Exception as e:
        print(f"Error during Qdrant search: {e}")
        results = []
    
    docs = []
    for res in results:
        # Fetch full data from MongoDB using mongo_id in payload
        mongo_id = res.payload.get("mongo_id")
        from bson import ObjectId
        doc = db_manager.sections_col.find_one({"_id": ObjectId(mongo_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            docs.append(doc)
            
    return {
        "retrieved_docs": docs,
        "reasoning_steps": state.get("reasoning_steps", []) + ["Retrieved top 3 semantic matches from Qdrant."]
    }

# Node 2: Legal Analyzer
def analyzer_node(state: AgentState):
    docs = state["retrieved_docs"]
    reasoning_steps = state.get("reasoning_steps", [])
    
    analyzed_docs = []
    for doc in docs:
        step = f"Analyzing Dafa {doc.get('dafa_no')} of {doc.get('act_name')}."
        if doc.get("symbol_found"):
            symbol = doc.get("symbol_found")
            step += f" Detected Amendment Marker ({symbol}), checking validity..."
            # Check amendment history from doc (already fetched from Mongo)
            history = doc.get("amendment_history")
            if history:
                step += f" Found history: {history}"
        reasoning_steps.append(step)
        analyzed_docs.append(doc)
        
    return {
        "retrieved_docs": analyzed_docs,
        "reasoning_steps": reasoning_steps
    }

# Node 3: BS-Date Tool
def date_tool_node(state: AgentState):
    question = state["question"]
    reasoning_steps = state.get("reasoning_steps", [])
    
    # Check if a date is mentioned in question (e.g., 2075)
    import re
    date_match = re.search(r"(\d{4})", question)
    if date_match:
        bs_year = date_match.group(1)
        ad_date = bs_to_ad(bs_year)
        reasoning_steps.append(f"Detected BS Date {bs_year}, converted to {ad_date} for Hada-myad (Statute of Limitations) check.")
        
    return {
        "reasoning_steps": reasoning_steps
    }

# Node 4: Synthesizer
def synthesizer_node(state: AgentState):
    question = state["question"]
    docs = state["retrieved_docs"]
    reasoning_steps = state["reasoning_steps"]
    
    if not docs:
        return {"final_answer": "I cannot find the specific law, please consult a lawyer."}
        
    context = ""
    for doc in docs:
        context += f"Act: {doc.get('act_name')}\nDafa: {doc.get('dafa_no')}\nContent: {doc.get('content')}\nAmendment History: {doc.get('amendment_history')}\n---\n"
        
    prompt = f"""Based on the provided Acts and the verified Amendment History, answer the user. If an amendment exists, you MUST mention it. Cite the Dafa and the Amendment Act explicitly.

User Question: {question}

Context:
{context}

Answer in Nepali (UTF-8).
"""
    response = model.generate_content(prompt)
    
    return {
        "final_answer": response.text
    }

# Build Graph
builder = StateGraph(AgentState)
builder.add_node("retriever", retriever_node)
builder.add_node("analyzer", analyzer_node)
builder.add_node("date_tool", date_tool_node)
builder.add_node("synthesizer", synthesizer_node)

builder.set_entry_point("retriever")
builder.add_edge("retriever", "analyzer")
builder.add_edge("analyzer", "date_tool")
builder.add_edge("date_tool", "synthesizer")
builder.add_edge("synthesizer", END)

graph = builder.compile()

if __name__ == "__main__":
    # Test Graph
    # inputs = {"question": "२०७५ मा भएको चोरीको घटनामा सजाय के हुन्छ?"}
    # for output in graph.stream(inputs):
    #     print(output)
    pass
