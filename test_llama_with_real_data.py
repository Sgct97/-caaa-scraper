#!/usr/bin/env python3
"""
Test Llama with REAL scraped CAAA messages
Using ACTUAL production prompts from ai_analyzer.py
"""

import json
from openai import OpenAI

# Initialize Ollama client (OpenAI-compatible API)
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Ollama doesn't need a real key
)

def test_relevance_analysis_llama(query: str, messages: list):
    """Test Llama on relevance analysis with real messages"""
    
    print("\n" + "="*80)
    print(f"TESTING LLAMA WITH REAL CAAA MESSAGES")
    print(f"Query: '{query}'")
    print("="*80)
    
    for i, msg in enumerate(messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"Subject: {msg.get('subject', 'No subject')}")
        print(f"From: {msg.get('message_from', 'Unknown')}")
        print(f"Date: {msg.get('date', 'No date')}")
        
        content = msg.get('content', '') or msg.get('body', '')
        if not content or len(content) < 20:
            print("⚠️  No content - skipping")
            continue
            
        print(f"Content length: {len(content)} chars")
        print(f"Content preview: {content[:200]}...")
        
        # Use ACTUAL production prompt from ai_analyzer.py
        prompt = f"""You are analyzing legal discussion messages from a California workers' compensation attorney listserv.

USER'S SEARCH QUERY: "{query}"

MESSAGE TO ANALYZE:
Subject: {msg.get('subject', 'No subject')}
From: {msg.get('message_from', 'Unknown')}
Date: {msg.get('date', 'No date')}

Content:
{content}

Your task:
Determine if this message is relevant to the user's search query and explain why.

Rate the relevance from 0 to 100:
- 0-20: Not relevant at all
- 21-40: Barely related
- 41-60: Somewhat relevant
- 61-80: Quite relevant
- 81-100: Highly relevant

Respond in JSON format:
{{
  "relevance_score": <number 0-100>,
  "ai_reasoning": "<1-2 sentence explanation of why this score was given>"
}}

Respond with ONLY valid JSON, no additional text."""

        print("\n🤖 Calling Llama 3.1 8B...")
        
        try:
            response = client.chat.completions.create(
                model="llama3.1:8b-instruct-q4_K_M",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing legal content for California workers' compensation law. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            result = response.choices[0].message.content
            print(f"\n📊 Llama Response:\n{result}")
            
            # Try to parse JSON
            try:
                parsed = json.loads(result)
                score = parsed.get('relevance_score')
                reasoning = parsed.get('ai_reasoning')
                
                print(f"\n✅ Score: {score}/100")
                print(f"   Reasoning: {reasoning}")
                
            except json.JSONDecodeError:
                print("\n❌ Failed to parse JSON response")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print("-" * 80)


if __name__ == "__main__":
    # Load real messages WITH CONTENT
    with open('real_messages_with_content.json', 'r') as f:
        messages = json.load(f)
    
    print(f"\n✓ Loaded {len(messages)} real CAAA messages with content")
    
    # Test with different queries relevant to the messages we have
    test_queries = [
        "QME panel requests",
        "apportionment in workers compensation",
        "medical legal evaluations"
    ]
    
    for query in test_queries:
        test_relevance_analysis_llama(query, messages)  # Test all messages
        
    print("\n" + "="*80)
    print("✅ TESTING COMPLETE")
    print("="*80)
    print("\nNow compare this to GPT-4 quality and decide if Llama is good enough!")

