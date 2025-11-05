#!/usr/bin/env python3
"""
FINAL AI COMPARISON: Llama 3.1 8B vs GPT-4o-mini
Test with real CAAA legal messages to make the final decision
"""

import json
import os
from openai import OpenAI

# Initialize both clients
llama_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

gpt_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def test_ai(client, model_name, query, message):
    """Test an AI model with a message"""
    content = message.get('body', '')
    subject = message.get('subject', 'No subject')
    
    prompt = f"""You are analyzing legal discussion messages from a California workers' compensation attorney listserv.

USER'S SEARCH QUERY: "{query}"

MESSAGE TO ANALYZE:
Subject: {subject}

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

    try:
        response = client.chat.completions.create(
            model=model_name,
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
        parsed = json.loads(result)
        return parsed
        
    except Exception as e:
        return {"error": str(e)}


def compare_models():
    """Run side-by-side comparison"""
    # Load messages
    with open('final_test_messages.json', 'r') as f:
        messages = json.load(f)
    
    print("\n" + "="*80)
    print("LLAMA 3.1 8B vs GPT-4o-mini - FINAL COMPARISON")
    print("="*80)
    print(f"\nTesting with {len(messages)} real CAAA legal messages\n")
    
    # Test queries
    test_queries = [
        "QME panel procedures",
        "apportionment case law",
        "penalties in workers compensation"
    ]
    
    llama_scores = []
    gpt_scores = []
    
    for query in test_queries:
        print("\n" + "="*80)
        print(f"QUERY: '{query}'")
        print("="*80)
        
        for i, msg in enumerate(messages[:3], 1):  # Test with first 3 messages per query
            subject = msg.get('subject', 'No subject')
            print(f"\n--- Message {i}: {subject[:60]}... ---")
            
            # Test Llama
            print("🦙 Llama 3.1 8B:")
            llama_result = test_ai(llama_client, "llama3.1:8b-instruct-q4_K_M", query, msg)
            if 'error' not in llama_result:
                llama_score = llama_result.get('relevance_score', 0)
                llama_scores.append(llama_score)
                print(f"   Score: {llama_score}/100")
                print(f"   Reasoning: {llama_result.get('ai_reasoning', 'N/A')[:100]}...")
            else:
                print(f"   ❌ Error: {llama_result['error']}")
            
            # Test GPT-4
            print("\n🤖 GPT-4o-mini:")
            gpt_result = test_ai(gpt_client, "gpt-4o-mini", query, msg)
            if 'error' not in gpt_result:
                gpt_score = gpt_result.get('relevance_score', 0)
                gpt_scores.append(gpt_score)
                print(f"   Score: {gpt_score}/100")
                print(f"   Reasoning: {gpt_result.get('ai_reasoning', 'N/A')[:100]}...")
            else:
                print(f"   ❌ Error: {gpt_result['error']}")
            
            # Show difference
            if 'error' not in llama_result and 'error' not in gpt_result:
                diff = abs(llama_score - gpt_score)
                if diff <= 10:
                    print(f"\n   ✅ Similar scores (diff: {diff})")
                elif diff <= 20:
                    print(f"\n   ⚠️  Moderate difference (diff: {diff})")
                else:
                    print(f"\n   ❌ Large difference (diff: {diff})")
    
    # Final stats
    print("\n" + "="*80)
    print("FINAL STATISTICS")
    print("="*80)
    
    if llama_scores and gpt_scores:
        llama_avg = sum(llama_scores) / len(llama_scores)
        gpt_avg = sum(gpt_scores) / len(gpt_scores)
        
        print(f"\n🦙 Llama 3.1 8B:")
        print(f"   Average score: {llama_avg:.1f}/100")
        print(f"   Cost per 1000 messages: $0")
        print(f"   Privacy: 100% (runs locally)")
        print(f"   HIPAA: ✅ Automatic")
        
        print(f"\n🤖 GPT-4o-mini:")
        print(f"   Average score: {gpt_avg:.1f}/100")
        print(f"   Cost per 1000 messages: ~$5-10")
        print(f"   Privacy: Data sent to OpenAI")
        print(f"   HIPAA: ❌ Needs BAA")
        
        print(f"\n📊 Comparison:")
        print(f"   Score difference: {abs(llama_avg - gpt_avg):.1f} points")
        
        if abs(llama_avg - gpt_avg) <= 10:
            print(f"   ✅ Quality: Essentially equal")
            print(f"\n   🎯 RECOMMENDATION: Use Llama 3.1 8B")
            print(f"      - Same quality, zero cost, 100% private")
        elif abs(llama_avg - gpt_avg) <= 20:
            print(f"   ⚠️  Quality: GPT-4 slightly better")
            print(f"\n   🎯 RECOMMENDATION: Depends on priorities")
            print(f"      - Llama: Free + private, slightly lower quality")
            print(f"      - GPT-4: Better quality, costs + privacy concerns")
        else:
            print(f"   ❌ Quality: GPT-4 significantly better")
            print(f"\n   🎯 RECOMMENDATION: Use GPT-4o-mini")
            print(f"      - Quality difference justifies the cost")


if __name__ == "__main__":
    compare_models()

