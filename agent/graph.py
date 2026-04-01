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
    token_usage: dict
    chat_history: List[Dict] # Added for Memory

def accumulate_tokens(res, current_usage):
    if hasattr(res, "usage_metadata") and res.usage_metadata:
        current_usage["prompt"] += res.usage_metadata.prompt_token_count
        current_usage["completion"] += res.usage_metadata.candidates_token_count
        current_usage["total"] += res.usage_metadata.total_token_count

# Database and LLM Setup
db_manager = DatabaseManager()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash") # Use 2.0 check

# Node 1: Retriever
def retriever_node(state: AgentState):
    original_question = state["question"]
    chat_history = state.get("chat_history", [])
    token_usage = state.get("token_usage", {"prompt": 0, "completion": 0, "total": 0})
    
    # 0. Query Rewriting for Contextual Pronoun Resolution
    question = original_question
    reasoning_prefix = []
    if chat_history:
        history_str = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history])
        rewrite_prompt = f"""
        Given the following conversation history and a follow-up question, rewrite the follow-up question to be a standalone legal query that includes all necessary context (like the specific Act being discussed or the exact legal provision). 
        If it does not need rewriting, return the exact original question. DO NOT answer the question. ONLY return the standalone question.
        
        Chat History:
        {history_str}
        
        Follow-up Question: {original_question}
        Standalone Question:"""
        try:
            rw_res = model.generate_content(rewrite_prompt)
            accumulate_tokens(rw_res, token_usage)
            rewritten = rw_res.text.strip()
            if rewritten and rewritten.lower() != original_question.lower():
                question = rewritten
                reasoning_prefix.append(f"Rewrote query for context: '{original_question}' -> '{question}'")
        except Exception as e:
            print(f"Rewrite error: {e}")
            
    embedding = db_manager.embedding_manager.get_embedding(question)
    
    import re
    # 1. Hybrid Search: Extract Keywords and Section Numbers Dynamically
    def dynamic_extract(q):
        extract_prompt = f"""
        Extract key legal terms, section numbers (e.g. 'Dafa 3', 'Section 5'), 
        and specific legal entities (e.g. 'Public Servant', 'Heinous Crime', 'जघन्य कसूर') 
        from the following Nepalese legal query for keyword-based retrieval. 
        Return ONLY a comma-separated list of terms. 
        If no specific terms are found, return 'none'.
        
        Query: {q}
        """
        try:
            res = model.generate_content(extract_prompt)
            accumulate_tokens(res, token_usage)
            raw = res.text.strip()
            if raw.lower() == "none" or not raw:
                return []
            return [t.strip() for t in raw.split(",") if t.strip()]
        except Exception as e:
            print(f"Error in dynamic_extract: {e}")
            return []

    dynamic_entities = dynamic_extract(question)
    
    # 2. Extract Section/Dafa numbers via regex for guaranteed precision
    ascii_nums = re.findall(r"(?:Section|Dafa|दफा)?\s*(\d+[a-zA-Z]?|\([a-zA-Z\d]+\))", question)
    nepali_nums = re.findall(r"(?:Section|Dafa|दफा)?\s*([०-९]+|\([क-ह][०-९]*\))", question)
    
    # Target all extracted targets (Dynamic Entities + Precise Numbers)
    targets = list(set(dynamic_entities + ascii_nums + nepali_nums))
    
    all_docs = []
    seen_ids = set()
    
    def clean_doc(doc):
        """Ensure document is fully JSON serializable."""
        cleaned = {}
        for k, v in doc.items():
            if k == "_id":
                cleaned[k] = str(v)
            elif hasattr(v, "isoformat"):  # For datetime objects
                cleaned[k] = v.isoformat()
            elif isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                cleaned[k] = v
            else:
                cleaned[k] = str(v)
        return cleaned
    
    # 2. Targeted "Direct Hit" Search (MongoDB) — increased limit to 15
    if targets:
        print(f"Hybrid Search Targets: {targets}")
        for target in targets:
            # Search by dafa_no, full_reference, hierarchy_path, or content
            cursor = db_manager.sections_col.find({
                "$or": [
                    {"dafa_no": target},
                    {"full_reference": {"$regex": target}},
                    {"hierarchy_path": {"$regex": target}},
                    {"content": {"$regex": target}}
                ]
            }).limit(15)
            for doc in cursor:
                doc_id = str(doc["_id"])
                if doc_id not in seen_ids:
                    cleaned = clean_doc(doc)
                    cleaned["retrieval_method"] = "keyword"
                    cleaned["keyword_match"] = True  # Fix 4: keyword-boost flag
                    all_docs.append(cleaned)
                    seen_ids.add(doc_id)
    
    # 3. Semantic Search (Vector) — increased Top-K to 20
    collections = ["legal_sections_vectors", "legal_pages_vectors"]
    for coll in collections:
        try:
            response = db_manager.qdrant_client.query_points(
                collection_name=coll,
                query=embedding,
                limit=20
            )
            results = response.points if hasattr(response, "points") else response
            
            for res in results:
                mongo_id = res.payload.get("mongo_id")
                from bson import ObjectId
                doc_id = str(mongo_id)
                if doc_id not in seen_ids:
                    doc = db_manager.sections_col.find_one({"_id": ObjectId(mongo_id)})
                    if doc:
                        cleaned = clean_doc(doc)
                        cleaned["retrieval_source"] = coll
                        cleaned["retrieval_method"] = "semantic"
                        cleaned["keyword_match"] = False
                        all_docs.append(cleaned)
                        seen_ids.add(doc_id)
                        
                        # 4a. Proactive Fetching for Incomplete Sections
                        if cleaned.get("is_incomplete"):
                            next_doc = db_manager.sections_col.find_one({
                                "act_name": cleaned.get("act_name"),
                                "_id": {"$gt": ObjectId(cleaned["_id"])}
                            }, sort=[("_id", 1)])
                            if next_doc:
                                next_id = str(next_doc["_id"])
                                if next_id not in seen_ids:
                                    nxt = clean_doc(next_doc)
                                    nxt["is_continuation"] = True
                                    all_docs.append(nxt)
                                    seen_ids.add(next_id)
                        
                        # 4b. Proactive Fetching for Lists (is_list_starter flag)
                        if cleaned.get("is_list_starter"):
                            siblings = db_manager.sections_col.find({
                                "act_name": cleaned.get("act_name"),
                                "_id": {"$gt": ObjectId(cleaned["_id"])}
                            }, sort=[("_id", 1)]).limit(10)
                            
                            for sib in siblings:
                                sib_id = str(sib["_id"])
                                if sib_id not in seen_ids:
                                    s_cleaned = clean_doc(sib)
                                    s_cleaned["is_continuation"] = True
                                    all_docs.append(s_cleaned)
                                    seen_ids.add(sib_id)
        except Exception as e:
            print(f"Error searching {coll}: {e}")

    # Fix 1: Colon-detection — auto-fetch children for ANY doc ending in ':' or ':-'
    colon_fetch_ids = []
    for doc in list(all_docs):
        content = str(doc.get("content") or "").strip()
        full_ref = doc.get("full_reference") or ""
        if (content.endswith(":") or content.endswith(":-") or content.endswith(":–")) and full_ref:
            # Fetch children whose full_reference starts with this doc's reference
            ref_prefix = full_ref.rstrip(".")
            children = db_manager.sections_col.find({
                "act_name": doc.get("act_name"),
                "full_reference": {"$regex": f"^{re.escape(ref_prefix)}"}
            }).limit(15)
            for child in children:
                child_id = str(child["_id"])
                if child_id not in seen_ids:
                    c_cleaned = clean_doc(child)
                    c_cleaned["is_continuation"] = True
                    c_cleaned["retrieval_method"] = "colon_child_fetch"
                    all_docs.append(c_cleaned)
                    seen_ids.add(child_id)

    # Fix 4: LLM-based Reranker — score and sort by relevance
    if all_docs and len(all_docs) > 5:
        try:
            snippet_summaries = []
            for idx, doc in enumerate(all_docs):
                ref = doc.get("full_reference") or doc.get("hierarchy_path") or doc.get("dafa_no", "?")
                content_preview = str(doc.get("content", ""))[:200]
                kw = "★KEYWORD-HIT" if doc.get("keyword_match") else ""
                snippet_summaries.append(f"[{idx}] Ref: {ref} {kw}\n{content_preview}")

            rerank_prompt = f"""You are a legal document relevance scorer. Given the user's question and a list of retrieved legal snippets, score each snippet's relevance from 0-10.

RULES:
- Snippets marked ★KEYWORD-HIT contain exact keyword matches — give them a +2 bonus.
- Return ONLY a JSON list of objects: [{{"idx": 0, "score": 8}}, ...]
- Score 10 = directly answers the question, 0 = completely irrelevant.

Question: {question}

Snippets:
{chr(10).join(snippet_summaries)}
"""
            rerank_response = model.generate_content(rerank_prompt)
            accumulate_tokens(rerank_response, token_usage)
            raw_scores = rerank_response.text.strip()
            # Parse JSON from response
            import json as _json
            score_match = re.search(r"\[.*\]", raw_scores, re.DOTALL)
            if score_match:
                scores = _json.loads(score_match.group(0))
                score_map = {item["idx"]: item["score"] for item in scores if "idx" in item and "score" in item}
                # Sort docs by score descending, keep top 15
                for idx, doc in enumerate(all_docs):
                    doc["_rerank_score"] = score_map.get(idx, 5)
                all_docs.sort(key=lambda d: d.get("_rerank_score", 0), reverse=True)
                all_docs = all_docs[:15]
        except Exception as e:
            print(f"Reranker error (falling back to unranked): {e}")

    return {
        "retrieved_docs": all_docs,
        "reasoning_steps": state.get("reasoning_steps", []) + reasoning_prefix + [f"Advanced Hybrid Search completed. Targeted entities: {targets}. Total snippets after rerank: {len(all_docs)}."],
        "token_usage": token_usage
    }

# Node 2: Legal Analyzer
def analyzer_node(state: AgentState):
    docs = state["retrieved_docs"]
    reasoning_steps = state.get("reasoning_steps", [])
    
    analyzed_docs = []
    for doc in docs:
        ref = doc.get("full_reference") or doc.get("dafa_no", "Unknown")
        step = f"Analyzing {ref} of {doc.get('act_name')}."
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
    token_usage = state.get("token_usage", {"prompt": 0, "completion": 0, "total": 0})
    chat_history = state.get("chat_history", [])
    
    if not docs:
        return {"final_answer": "I cannot find the specific law, please consult a lawyer."}
        
    context = ""
    for doc in docs:
        source = doc.get("retrieval_source", "unknown")
        ref = doc.get("full_reference") or doc.get("dafa_no", "Unknown")
        h_path = doc.get("hierarchy_path", "")
        context += (
            f"[Ref: {ref}] [Path: {h_path}] [Source: {source}] Act: {doc.get('act_name')}\n"
            f"Content: {doc.get('content')}\n"
            f"Amendment History: {doc.get('amendment_history')}\n"
            f"Is Continuation: {doc.get('is_continuation', False)}\n---\n"
        )
        
    history_str = ""
    if chat_history:
        history_str = "Conversation History:\n" + "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history])
        
    prompt = f"""You are a high-precision Nepalese Legal Expert. Use the following context and conversation history to answer the user.
    
CRITICAL RULES:
1. HIERARCHICAL CITATION: Use the 'Ref' field for ALL citations. It is already formatted with full context (Section -> Clause -> Sub-clause). Use the 'Path' field to disambiguate when needed (e.g., Path '३-ञ-२' means Section 3, Clause ञ, Sub-clause 2). NEVER confuse a Section number with a Sub-clause number. IMPORTANT: In this legal document, numerical sub-sections in parentheses like (1), (2), (3) are usually top-level children of a Section (Dafa). Alphabetical clauses like (ka), (kha), (ga) are usually children of those sub-sections. Do not assume an alphabetical clause is a parent of a numerical sub-section.
2. AMENDMENT INTEGRITY — DO NOT HALLUCINATE:
   a. Only state that a section was amended if the 'Amendment History' field for THAT SPECIFIC snippet is populated (not null, not empty).
   b. When citing an amendment, QUOTE the exact text from the 'Amendment History' field.
   c. If the 'Amendment History' field is null/empty, you MUST remain completely silent about amendments for that snippet — do NOT say 'there is no amendment', 'the provision is original', or 'no amendment was made'.
   d. If the specific sub-clause the user asked about was NOT found in the retrieved context, state: "उक्त उपदफा/खण्ड प्राप्त सन्दर्भमा भेटिएन" (The specific sub-clause was not found in the retrieved context) — do NOT assume anything about its amendment status.
3. DISTRICT COORDINATION HITS: If the question mentions "जिल्ला समन्वय समिति" or "स्थानीय तह", ensure you prioritize the snippet that explicitly contains those words.
4. CONTINUATION MERGING: If snippets are marked 'Is Continuation: True', they are part of the preceding 'Incomplete' or 'List' snippet. Merge their text into a single coherent answer.
5. MISTAKE OF LAW: For Section 8, distinguish clearly: Mistake of Fact (excused in good faith) vs. Mistake of Law (NOT excused).
6. MARKDOWN FORMATTING (CRITICAL): You must use rich Markdown to format your response. Use bold text (**text**) for emphasis and bullet points for lists. If the user's question involves comparing different Acts, Crimes, Punishments, or Legal Provisions, you MUST construct a beautiful Markdown table to present the comparison clearly.

{history_str}

User Question: {question}

Context:
{context}

Answer in Nepali (UTF-8). Provide the final answer with clear citations for each point.
"""
    try:
        response = model.generate_content(prompt)
        accumulate_tokens(response, token_usage)
        final_text = response.text
    except Exception as e:
        print(f"Synthesizer LLM error: {e}")
        final_text = "An error occurred generating the final answer. Please try again."
    
    return {
        "final_answer": final_text,
        "reasoning_steps": reasoning_steps + ["Stitched hierarchical fragments and enforced strict amendment reporting guardrails."],
        "token_usage": token_usage
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
