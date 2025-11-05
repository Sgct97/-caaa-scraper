#!/usr/bin/env python3
"""
Test local Llama model against our AI tasks:
1. Query Enhancement (convert natural language to search params)
2. Relevance Analysis (score message relevance)
"""

import json
from datetime import datetime, timedelta
import subprocess

def call_ollama(prompt: str, system: str = None) -> str:
    """Call local Ollama model"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    # Call ollama via subprocess
    cmd = [
        "ollama", "run", "llama3.1:8b-instruct-q4_K_M",
        prompt
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def test_query_enhancement():
    """Test 1: Query Enhancement"""
    print("\n" + "="*80)
    print("TEST 1: QUERY ENHANCEMENT")
    print("="*80)
    
    # Current date context
    today = datetime.now()
    three_months_ago = (today - timedelta(days=90)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    
    test_queries = [
        "I'm looking for recent cases John Smith has had involving a doctor",
        "permanent disability ratings",
        "workers compensation medical treatment guidelines from 2024",
    ]
    
    for query in test_queries:
        print(f"\n📝 User Query: \"{query}\"")
        print("-" * 80)
        
        prompt = f"""You are an expert legal research assistant for California workers' compensation law.

TODAY'S DATE: {today_str}

USER'S QUERY: "{query}"

Your task: Extract search parameters from the user's query.

IMPORTANT RULES:
- If user says "recent", suggest dates from 3 months ago ({three_months_ago}) to TODAY ({today_str})
- DO NOT add date filters unless user specifically mentions time periods
- Extract any names mentioned
- Identify relevant keywords

Respond in JSON format:
{{
  "keywords_any": "space-separated keywords or null",
  "keywords_all": "keywords that must all appear or null",
  "keywords_phrase": "exact phrase or null",
  "date_from": "YYYY-MM-DD or null",
  "date_to": "YYYY-MM-DD or null",
  "author_last_name": "last name or null",
  "listserv": "all/lamaaa/lavaaa/lawnet/scaaa",
  "reasoning": "brief explanation of your choices"
}}

Respond with ONLY valid JSON, no extra text."""

        print("🤖 Llama Response:")
        response = call_ollama(prompt)
        print(response)
        
        # Try to parse JSON
        try:
            parsed = json.loads(response)
            print("\n✅ Valid JSON!")
            print(f"   Keywords: {parsed.get('keywords_any') or parsed.get('keywords_all')}")
            print(f"   Dates: {parsed.get('date_from')} to {parsed.get('date_to')}")
            print(f"   Author: {parsed.get('author_last_name')}")
        except:
            print("\n❌ Invalid JSON - needs refinement")


def test_relevance_analysis():
    """Test 2: Relevance Analysis"""
    print("\n" + "="*80)
    print("TEST 2: RELEVANCE ANALYSIS")
    print("="*80)
    
    test_cases = [
        {
            "query": "medical treatment guidelines",
            "message": """Subject: Question about MTUS guidelines
            
Hi everyone, I have a question about the Medical Treatment Utilization Schedule (MTUS). 
My client needs chronic pain treatment but the adjuster is denying it citing MTUS. 
Has anyone dealt with this? What's the best way to argue for treatment outside MTUS guidelines?

Thanks,
John""",
            "expected_score": "high (80-95)"
        },
        {
            "query": "medical treatment",
            "message": """Subject: Looking for orthopedic expert in Sacramento

Anyone have recommendations for a good orthopedic QME in the Sacramento area? 
Need someone who is fair and thorough for a back injury case.

Thanks!""",
            "expected_score": "medium (40-60)"
        },
        {
            "query": "medical treatment",
            "message": """Subject: Office space for rent

Hi colleagues, I'm moving my practice and have office space available to sublet 
in downtown LA. 2 offices, shared conference room. $1200/month. Contact me if interested.""",
            "expected_score": "low (0-20)"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📧 Test Case {i}:")
        print(f"   Query: \"{test['query']}\"")
        print(f"   Expected: {test['expected_score']}")
        print("-" * 80)
        
        prompt = f"""You are analyzing if a message is relevant to a user's search query.

USER'S QUERY: "{test['query']}"

MESSAGE CONTENT:
{test['message']}

Your task:
1. Rate relevance from 0-100 (0=completely irrelevant, 100=perfectly matches)
2. Explain your reasoning in 1-2 sentences

Respond in JSON format:
{{
  "relevance_score": 0-100,
  "reasoning": "brief explanation"
}}

Respond with ONLY valid JSON, no extra text."""

        print("🤖 Llama Response:")
        response = call_ollama(prompt)
        print(response)
        
        # Try to parse JSON
        try:
            parsed = json.loads(response)
            print(f"\n✅ Score: {parsed.get('relevance_score')}/100")
            print(f"   Reasoning: {parsed.get('reasoning')}")
        except:
            print("\n❌ Invalid JSON - needs refinement")


if __name__ == "__main__":
    print("\n🦙 Testing Local Llama 3.1 8B for CAAA Scraper AI Tasks")
    print("="*80)
    
    test_query_enhancement()
    test_relevance_analysis()
    
    print("\n" + "="*80)
    print("✅ Testing Complete!")
    print("="*80)

