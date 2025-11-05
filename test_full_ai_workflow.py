#!/usr/bin/env python3
"""
COMPREHENSIVE AI TEST - Exactly mimics production workflow
Tests both AI layers with realistic scenarios
"""

import json
from openai import OpenAI
from datetime import datetime, timedelta

llama = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

def test_query_enhancement(user_query):
    """TEST 1: Query Enhancement - Convert natural language to search params"""
    
    today = datetime.now()
    three_months_ago = (today - timedelta(days=90)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    
    prompt = f"""You are an expert legal research assistant for California workers' compensation law.

TODAY'S DATE: {today_str}

USER'S QUERY: "{user_query}"

Extract search parameters from the user's query.

IMPORTANT RULES:
- If user says "recent", suggest dates from 3 months ago ({three_months_ago}) to TODAY ({today_str})
- If user mentions a year like "2024", use that year's date range
- DO NOT add date filters unless user specifically mentions time periods
- Extract any names mentioned
- Identify relevant keywords

Examples:
- "recent cases" = date_from: {three_months_ago}, date_to: {today_str}
- "John Smith medical" = keywords_any: "medical", author_last_name: "Smith"
- "permanent disability" = keywords_phrase: "permanent disability"

Respond in JSON format:
{{
  "keywords_any": "space-separated keywords or null",
  "keywords_all": "keywords that must all appear or null",
  "keywords_phrase": "exact phrase or null",
  "date_from": "YYYY-MM-DD or null",
  "date_to": "YYYY-MM-DD or null",
  "author_last_name": "last name or null",
  "listserv": "all/lamaaa/lavaaa/lawnet/scaaa",
  "reasoning": "brief explanation"
}}

Respond with ONLY valid JSON."""

    response = llama.chat.completions.create(
        model="llama3.1:8b-instruct-q4_K_M",
        messages=[
            {"role": "system", "content": "You are a California workers' compensation legal research expert. Respond only with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=400
    )
    
    return json.loads(response.choices[0].message.content)


def test_relevance_filtering(query, messages):
    """TEST 2: Relevance Filtering - Score messages for relevance"""
    
    results = []
    
    for msg in messages:
        content = msg.get('body', '')
        subject = msg.get('subject', 'No subject')
        
        prompt = f"""You are analyzing legal discussion messages from a California workers' compensation attorney listserv.

USER'S SEARCH QUERY: "{query}"

MESSAGE TO ANALYZE:
Subject: {subject}

Content:
{content[:1000]}  

STRICT SCORING RULES:
- 90-100: Message DIRECTLY answers or discusses the query topic in detail
- 70-89: Message discusses the query topic with substantial content
- 50-69: Message mentions the query topic but is mostly about something else
- 30-49: Message has only tangential connection
- 10-29: Message barely mentions something related
- 0-9: Not relevant at all

IMPORTANT:
- Simple "thank you" or acknowledgments = 0-20 points
- Just mentioning a keyword is NOT enough
- Be STRICT and CONSERVATIVE

Respond in JSON format:
{{
  "relevance_score": <number 0-100>,
  "ai_reasoning": "<explanation starting with 'Low/Medium/High relevance:' based on score>"
}}

Respond with ONLY valid JSON."""

        response = llama.chat.completions.create(
            model="llama3.1:8b-instruct-q4_K_M",
            messages=[
                {"role": "system", "content": "You are a STRICT legal relevance analyzer. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        result = json.loads(response.choices[0].message.content)
        result['subject'] = subject[:60]
        results.append(result)
    
    return results


def run_comprehensive_test():
    """Run full workflow test"""
    
    # Load messages
    with open('comprehensive_test_messages.json', 'r') as f:
        messages = json.load(f)
    
    print("\n" + "="*80)
    print("COMPREHENSIVE AI WORKFLOW TEST - Production Simulation")
    print("="*80)
    
    # Test scenarios
    test_scenarios = [
        {
            "user_query": "I'm looking for recent cases where John Smith dealt with QME panels",
            "expected_fields": ["author_last_name: Smith", "keywords about QME", "recent dates"]
        },
        {
            "user_query": "permanent disability ratings from 2024",
            "expected_fields": ["keywords: permanent disability", "dates: 2024"]
        },
        {
            "user_query": "medical treatment authorization disputes",
            "expected_fields": ["keywords: medical treatment authorization", "no date filter"]
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*80}")
        print(f"TEST SCENARIO {i}")
        print(f"{'='*80}")
        print(f"\nUser Query: \"{scenario['user_query']}\"")
        print(f"Expected: {', '.join(scenario['expected_fields'])}")
        
        # TEST 1: Query Enhancement
        print(f"\n--- AI LAYER 1: Query Enhancement ---")
        enhanced = test_query_enhancement(scenario['user_query'])
        print(f"✓ AI Generated Search Params:")
        for key, val in enhanced.items():
            if val and key != 'reasoning':
                print(f"  - {key}: {val}")
        print(f"  Reasoning: {enhanced.get('reasoning', 'N/A')[:80]}...")
        
        # TEST 2: Relevance Filtering
        print(f"\n--- AI LAYER 2: Relevance Filtering ---")
        # Simulate what query user actually meant
        test_query = scenario['user_query'].split()[0:4]  # First few words
        test_query_str = ' '.join(test_query)
        
        print(f"Testing relevance with query: '{test_query_str}'")
        print(f"Analyzing {len(messages)} messages...")
        
        scored_messages = test_relevance_filtering(test_query_str, messages[:5])  # Test with 5 messages
        
        # Show results
        high = [m for m in scored_messages if m['relevance_score'] >= 70]
        medium = [m for m in scored_messages if 40 <= m['relevance_score'] < 70]
        low = [m for m in scored_messages if m['relevance_score'] < 40]
        
        print(f"\n📊 Results:")
        print(f"  High relevance (70-100): {len(high)}")
        print(f"  Medium relevance (40-69): {len(medium)}")
        print(f"  Low relevance (0-39): {len(low)}")
        
        print(f"\n  Top 3 by relevance:")
        sorted_msgs = sorted(scored_messages, key=lambda x: x['relevance_score'], reverse=True)
        for j, msg in enumerate(sorted_msgs[:3], 1):
            print(f"    {j}. [{msg['relevance_score']}/100] {msg['subject']}...")
            print(f"       {msg['ai_reasoning'][:100]}...")
    
    print(f"\n{'='*80}")
    print("COMPREHENSIVE TEST COMPLETE")
    print(f"{'='*80}")
    print("\n✅ If Llama performed well above, it's ready for production!")
    print("   - Query enhancement should extract correct fields")
    print("   - Relevance scores should match message content accurately")
    print("   - High scores for relevant, low scores for irrelevant")


if __name__ == "__main__":
    run_comprehensive_test()

