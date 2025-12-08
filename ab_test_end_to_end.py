#!/usr/bin/env python3
"""
End-to-End A/B Test: Local LLM vs GPT-4o-mini
Actually runs searches and shows results for human comparison.

Usage:
    export OPENAI_API_KEY="your-key"
    python ab_test_end_to_end.py "your search query here"
"""

import sys
import json
import os
import time
from datetime import datetime
from openai import OpenAI

# Local imports
from search_params import SearchParams
from database import Database
from scraper import CAAASessionManager

# ============================================================
# Configuration
# ============================================================

LOCAL_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
LOCAL_MODEL = "qwen2.5:32b"
GPT_MODEL = "gpt-4o-mini"

# ============================================================
# Query Enhancement
# ============================================================

def enhance_with_local(query: str) -> dict:
    """Get search params from LOCAL LLM"""
    try:
        client = OpenAI(base_url=LOCAL_OLLAMA_URL, api_key="ollama")
        prompt = _build_enhancer_prompt(query)
        
        response = client.chat.completions.create(
            model=LOCAL_MODEL,
            messages=[
                {"role": "system", "content": "You convert search queries to JSON parameters. Respond with ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        import re
        json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}
    except Exception as e:
        print(f"   ❌ Local error: {e}")
        return {}


def enhance_with_gpt(query: str) -> dict:
    """Get search params from GPT"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("   ❌ OPENAI_API_KEY not set")
        return {}
    
    try:
        client = OpenAI(api_key=api_key)
        prompt = _build_enhancer_prompt(query)
        
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You convert search queries to JSON parameters. Respond with ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        import re
        json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}
    except Exception as e:
        print(f"   ❌ GPT error: {e}")
        return {}


def _build_enhancer_prompt(query: str) -> str:
    return f"""Convert this search query into parameters for a legal listserv search.

QUERY: "{query}"

Available fields:
- keywords_all: Terms that MUST all appear
- keywords_any: Terms where at least ONE must appear  
- keywords_phrase: Exact phrase match
- keywords_exclude: Terms to exclude
- author_first_name: Witness/Expert first name
- author_last_name: Witness/Expert last name
- posted_by: Who SENT the message (full name)
- date_from: Start date (YYYY-MM-DD) - use for "recent" queries (6 months ago)
- date_to: End date (YYYY-MM-DD)

RULES:
- "messages BY X" / "from X" → posted_by
- "QME Dr. X" / "expert X" → author_first_name + author_last_name
- "mentioning X" / "about X" → keywords_any
- "recent" / "latest" → date_from = 6 months ago

Return ONLY JSON like: {{"keywords_any": "term1, term2", "posted_by": "John Smith"}}
"""


# ============================================================
# AI Analysis
# ============================================================

def analyze_with_local(query: str, messages: list) -> list:
    """Analyze messages with LOCAL LLM"""
    client = OpenAI(base_url=LOCAL_OLLAMA_URL, api_key="ollama")
    results = []
    
    for msg in messages:
        try:
            prompt = _build_analyzer_prompt(query, msg)
            response = client.chat.completions.create(
                model=LOCAL_MODEL,
                messages=[
                    {"role": "system", "content": "Analyze message relevance. Respond with ONLY JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content
            import re
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                results.append({
                    "message_id": msg.get("id"),
                    "subject": msg.get("subject", "")[:60],
                    "from": msg.get("from", "")[:40],
                    "score": analysis.get("relevance_score", 0),
                    "reasoning": analysis.get("reasoning", "")[:100]
                })
        except Exception as e:
            results.append({"message_id": msg.get("id"), "error": str(e)})
    
    return results


def analyze_with_gpt(query: str, messages: list) -> list:
    """Analyze messages with GPT"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return [{"error": "OPENAI_API_KEY not set"}]
    
    client = OpenAI(api_key=api_key)
    results = []
    
    for msg in messages:
        try:
            prompt = _build_analyzer_prompt(query, msg)
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "Analyze message relevance. Respond with ONLY JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content
            import re
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                results.append({
                    "message_id": msg.get("id"),
                    "subject": msg.get("subject", "")[:60],
                    "from": msg.get("from", "")[:40],
                    "score": analysis.get("relevance_score", 0),
                    "reasoning": analysis.get("reasoning", "")[:100]
                })
        except Exception as e:
            results.append({"message_id": msg.get("id"), "error": str(e)})
    
    return results


def _build_analyzer_prompt(query: str, msg: dict) -> str:
    return f"""Is this message relevant to: "{query}"

From: {msg.get('from', 'Unknown')}
Subject: {msg.get('subject', 'No subject')}
Body: {msg.get('body', '')[:500]}...

Rate 0-100 (0=irrelevant, 100=highly relevant)
Return JSON: {{"relevance_score": <number>, "reasoning": "<brief explanation>"}}
"""


# ============================================================
# Search Execution
# ============================================================

def run_search(params: dict, max_messages: int = 20) -> list:
    """Actually run a search with given params and return messages"""
    try:
        # Convert dict to SearchParams
        search_params = SearchParams(
            keywords_all=params.get("keywords_all"),
            keywords_any=params.get("keywords_any"),
            keywords_phrase=params.get("keywords_phrase"),
            keywords_exclude=params.get("keywords_exclude"),
            author_first_name=params.get("author_first_name"),
            author_last_name=params.get("author_last_name"),
            posted_by=params.get("posted_by"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
            listserv=params.get("listserv", "all"),
            max_messages=max_messages
        )
        
        # Use the scraper to run the search
        scraper = CAAASessionManager()
        messages = scraper.search_and_fetch(search_params)
        
        return messages
        
    except Exception as e:
        print(f"   ❌ Search error: {e}")
        return []


# ============================================================
# Main Test
# ============================================================

def run_ab_test(query: str, max_messages: int = 15):
    """Run full end-to-end A/B test"""
    
    print("\n" + "="*80)
    print(f"END-TO-END A/B TEST")
    print(f"Query: \"{query}\"")
    print("="*80)
    
    # Step 1: Query Enhancement
    print("\n" + "-"*40)
    print("STEP 1: QUERY ENHANCEMENT")
    print("-"*40)
    
    print(f"\n🦙 LOCAL ({LOCAL_MODEL}):")
    local_params = enhance_with_local(query)
    print(f"   Params: {json.dumps(local_params, indent=2)}")
    
    print(f"\n🤖 GPT ({GPT_MODEL}):")
    gpt_params = enhance_with_gpt(query)
    print(f"   Params: {json.dumps(gpt_params, indent=2)}")
    
    # Step 2: Run Searches
    print("\n" + "-"*40)
    print("STEP 2: RUNNING SEARCHES")
    print("-"*40)
    
    print(f"\n🦙 Running search with LOCAL params...")
    local_messages = run_search(local_params, max_messages)
    print(f"   Found: {len(local_messages)} messages")
    
    print(f"\n🤖 Running search with GPT params...")
    gpt_messages = run_search(gpt_params, max_messages)
    print(f"   Found: {len(gpt_messages)} messages")
    
    # Use combined unique messages for analysis comparison
    all_messages = {m.get('id', m.get('subject')): m for m in local_messages + gpt_messages}
    unique_messages = list(all_messages.values())[:20]  # Limit for analysis
    
    print(f"\n📊 Total unique messages for analysis: {len(unique_messages)}")
    
    if not unique_messages:
        print("\n❌ No messages found. Cannot continue test.")
        return
    
    # Step 3: AI Analysis
    print("\n" + "-"*40)
    print("STEP 3: AI RELEVANCE ANALYSIS")
    print("-"*40)
    
    print(f"\n🦙 Analyzing with LOCAL ({LOCAL_MODEL})...")
    local_analysis = analyze_with_local(query, unique_messages)
    
    print(f"\n🤖 Analyzing with GPT ({GPT_MODEL})...")
    gpt_analysis = analyze_with_gpt(query, unique_messages)
    
    # Step 4: Compare Results
    print("\n" + "="*80)
    print("RESULTS COMPARISON")
    print("="*80)
    
    print("\n📊 SEARCH PARAMS COMPARISON:")
    print(f"   LOCAL: {local_params}")
    print(f"   GPT:   {gpt_params}")
    
    print(f"\n📊 MESSAGES FOUND:")
    print(f"   LOCAL params found: {len(local_messages)} messages")
    print(f"   GPT params found:   {len(gpt_messages)} messages")
    
    print("\n📊 RELEVANCE SCORES (side-by-side):")
    print("-"*80)
    print(f"{'Subject':<40} | {'LOCAL':>8} | {'GPT':>8} | {'Diff':>6}")
    print("-"*80)
    
    local_scores = []
    gpt_scores = []
    
    for i, (local_r, gpt_r) in enumerate(zip(local_analysis, gpt_analysis)):
        subject = local_r.get("subject", "???")[:38]
        local_score = local_r.get("score", "ERR")
        gpt_score = gpt_r.get("score", "ERR")
        
        if isinstance(local_score, (int, float)) and isinstance(gpt_score, (int, float)):
            diff = local_score - gpt_score
            local_scores.append(local_score)
            gpt_scores.append(gpt_score)
            print(f"{subject:<40} | {local_score:>8} | {gpt_score:>8} | {diff:>+6}")
        else:
            print(f"{subject:<40} | {str(local_score):>8} | {str(gpt_score):>8} | {'N/A':>6}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if local_scores and gpt_scores:
        local_avg = sum(local_scores) / len(local_scores)
        gpt_avg = sum(gpt_scores) / len(gpt_scores)
        
        print(f"\n   LOCAL avg relevance score: {local_avg:.1f}")
        print(f"   GPT avg relevance score:   {gpt_avg:.1f}")
        print(f"   Difference: {abs(local_avg - gpt_avg):.1f} points")
        
        # Count agreements
        agreements = sum(1 for l, g in zip(local_scores, gpt_scores) if abs(l - g) <= 15)
        print(f"\n   Agreements (within 15 pts): {agreements}/{len(local_scores)} ({agreements/len(local_scores)*100:.0f}%)")
    
    print("\n" + "-"*40)
    print("TOP RESULTS - LOCAL ANALYSIS")
    print("-"*40)
    sorted_local = sorted([r for r in local_analysis if "score" in r], key=lambda x: x["score"], reverse=True)[:5]
    for r in sorted_local:
        print(f"   [{r['score']:>3}] {r['subject']}")
        print(f"         {r.get('reasoning', '')[:70]}...")
    
    print("\n" + "-"*40)
    print("TOP RESULTS - GPT ANALYSIS")
    print("-"*40)
    sorted_gpt = sorted([r for r in gpt_analysis if "score" in r], key=lambda x: x["score"], reverse=True)[:5]
    for r in sorted_gpt:
        print(f"   [{r['score']:>3}] {r['subject']}")
        print(f"         {r.get('reasoning', '')[:70]}...")
    
    # Save full results
    output = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "local_params": local_params,
        "gpt_params": gpt_params,
        "local_messages_count": len(local_messages),
        "gpt_messages_count": len(gpt_messages),
        "local_analysis": local_analysis,
        "gpt_analysis": gpt_analysis
    }
    
    filename = f"ab_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n📁 Full results saved to: {filename}")
    print("\n🎯 NOW YOU DECIDE: Which model gave better results for your use case?")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ab_test_end_to_end.py \"your search query\"")
        print("\nExample queries to test:")
        print('  python ab_test_end_to_end.py "recent changes to paterson case"')
        print('  python ab_test_end_to_end.py "messages from Ray Saedi"')
        print('  python ab_test_end_to_end.py "QME panel procedures"')
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  OPENAI_API_KEY not set. GPT tests will fail.")
        print("   export OPENAI_API_KEY='sk-your-key'")
    
    run_ab_test(query)

