#!/usr/bin/env python3
"""
Test Llama with IMPROVED, more conservative prompt
Goal: Make Llama score as accurately as GPT-4
"""

import json
from openai import OpenAI

llama_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

def test_llama_improved(query, message):
    """Test Llama with improved prompt"""
    content = message.get('body', '')
    subject = message.get('subject', 'No subject')
    
    # IMPROVED PROMPT - More conservative scoring
    prompt = f"""You are analyzing legal discussion messages from a California workers' compensation attorney listserv.

USER'S SEARCH QUERY: "{query}"

MESSAGE TO ANALYZE:
Subject: {subject}

Content:
{content}

Your task:
Determine if this message is DIRECTLY RELEVANT to the user's search query.

STRICT SCORING RULES:
- 90-100: Message DIRECTLY answers or discusses the query topic in detail
- 70-89: Message discusses the query topic with substantial content
- 50-69: Message mentions the query topic but is mostly about something else
- 30-49: Message has only tangential connection to the query
- 10-29: Message barely mentions something related to the query
- 0-9: Message is not relevant at all

IMPORTANT:
- A simple "thank you" or acknowledgment is 0-20 points, even if it's replying to a relevant thread
- Just mentioning a keyword is NOT enough - the message must actually DISCUSS the topic
- Be STRICT and CONSERVATIVE with scores
- A message about Topic A is NOT highly relevant to a query about Topic B, even if related

Respond in JSON format:
{{
  "relevance_score": <number 0-100>,
  "ai_reasoning": "<1-2 sentence explanation. Start with: 'Low relevance:' or 'Medium relevance:' or 'High relevance:' based on score>"
}}

Respond with ONLY valid JSON, no additional text."""

    try:
        response = llama_client.chat.completions.create(
            model="llama3.1:8b-instruct-q4_K_M",
            messages=[
                {
                    "role": "system",
                    "content": "You are a STRICT legal relevance analyzer. You give LOW scores to barely-relevant content and HIGH scores only to directly relevant content. Respond only with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Lower temperature for more consistent/conservative scoring
            max_tokens=300
        )
        
        result = response.choices[0].message.content
        parsed = json.loads(result)
        return parsed
        
    except Exception as e:
        return {"error": str(e)}


def test_improved_prompt():
    """Test with the same messages"""
    with open('final_test_messages.json', 'r') as f:
        messages = json.load(f)
    
    print("\n" + "="*80)
    print("LLAMA 3.1 8B - IMPROVED CONSERVATIVE PROMPT")
    print("="*80)
    
    test_cases = [
        ("QME panel procedures", messages[1]),  # The "thank you" message
        ("penalties in workers compensation", messages[2]),  # The penalty case
        ("apportionment case law", messages[0]),  # Judge Diamond case
    ]
    
    print("\nTesting with improved, more conservative prompt:\n")
    
    for query, msg in test_cases:
        subject = msg.get('subject', 'No subject')[:60]
        print(f"\nQuery: '{query}'")
        print(f"Message: {subject}...")
        print(f"Content preview: {msg.get('body','')[:150]}...")
        
        result = test_llama_improved(query, msg)
        
        if 'error' not in result:
            score = result.get('relevance_score', 0)
            reasoning = result.get('ai_reasoning', 'N/A')
            print(f"\n🦙 Llama Score: {score}/100")
            print(f"   Reasoning: {reasoning}")
        else:
            print(f"\n❌ Error: {result['error']}")
        
        print("-" * 80)


if __name__ == "__main__":
    test_improved_prompt()

