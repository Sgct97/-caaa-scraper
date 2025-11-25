#!/usr/bin/env python3
"""
AI Analyzer Module
Uses OpenAI to determine if messages are relevant to search queries
"""

import os
from typing import Dict, Optional
import json
from openai import OpenAI


class AIAnalyzer:
    """Analyzes message relevance using OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize AI analyzer
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4o-mini for cost efficiency)
        """
        # Use Vast.ai GPU with Qwen 32B via SSH tunnel for fast, HIPAA-compliant processing
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
        self.client = OpenAI(
            base_url=ollama_url,
            api_key="ollama"
        )
        self.model = "qwen2.5:32b"
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
    
    def analyze_relevance(self, 
                         message: Dict[str, str],
                         search_keyword: str,
                         additional_context: Optional[str] = None) -> Dict:
        """
        Analyze if a message is relevant to the search keyword
        
        Args:
            message: Dict with keys: subject, body, from_name
            search_keyword: The keyword/phrase being searched
            additional_context: Optional additional search context
        
        Returns:
            Dict with:
                - is_relevant: bool
                - confidence: float (0.0-1.0)
                - reasoning: str
                - tokens_used: int
                - cost_usd: float
        """
        
        # Build prompt
        prompt = self._build_prompt(message, search_keyword, additional_context)
        
        try:
            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert legal assistant analyzing workers' compensation case law and listserv messages. Your job is to determine if a message is genuinely relevant to a user's search query."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.0,  # Zero temperature for deterministic results
                max_tokens=500
            )
            
            # Parse response
            result = self._parse_response(response)
            
            # Track usage
            tokens_used = response.usage.total_tokens
            cost = self._calculate_cost(tokens_used, self.model)
            
            self.total_tokens_used += tokens_used
            self.total_cost_usd += cost
            
            result['ai_tokens_used'] = tokens_used
            result['ai_cost_usd'] = cost
            result['ai_model'] = self.model
            result['ai_reasoning'] = result.pop('reasoning')  # Rename for DB compatibility
            
            return result
            
        except Exception as e:
            print(f"❌ Error calling OpenAI: {e}")
            # Return default "not relevant" on error
            return {
                'is_relevant': False,
                'confidence': 0.0,
                'ai_reasoning': f"Error analyzing message: {str(e)}",
                'ai_tokens_used': 0,
                'ai_cost_usd': 0.0,
                'ai_model': self.model
            }
    
    def _build_prompt(self, message: Dict, search_keyword: str, context: Optional[str]) -> str:
        """Build the prompt for OpenAI"""
        
        subject = message.get('subject', 'No subject')
        body = message.get('body', '')
        from_name = message.get('from_name', 'Unknown')
        
        # Truncate body if too long (to save tokens)
        max_body_length = 2000
        if len(body) > max_body_length:
            body = body[:max_body_length] + "... [truncated]"
        
        prompt = f"""You are an expert California workers' compensation attorney analyzing a listserv message from CAAA (California Applicants' Attorneys Association) to determine if it provides substantive information that helps answer a specific legal question.

CONTEXT:
This message is from a professional legal discussion forum where experienced workers' compensation attorneys discuss case strategies, statutory interpretations, procedural questions, and share practical insights from their practice.

USER'S LEGAL QUESTION:
"{search_keyword}"
{f'ADDITIONAL CONTEXT: {context}' if context else ''}

LISTSERV MESSAGE:
From: {from_name}
Subject: {subject}

{body}

🚨 CRITICAL RULE - AUTHOR-FOCUSED SEARCHES 🚨
IF the user's question is ONLY asking for messages FROM or MENTIONING a specific person (examples: "messages from Ray Saedi", "posts by John Smith", "find ALL messages from author: Johnson", "anything mentioning Sarah"), then:
- IGNORE all content analysis rules below
- Mark as RELEVANT (is_relevant: true) if the message is FROM that person OR clearly MENTIONS that person
- Set confidence to 0.95 if from that person, 0.85 if mentioning them
- Reasoning: Simply state "Message from [name]" or "Message mentions [name]"
- DO NOT judge content quality, substantiveness, or legal insight

ANALYSIS REQUIREMENTS (for content-based searches):

Evaluate whether this message provides actionable legal insight that helps answer the user's question. Consider:

1. SUBSTANTIVE LEGAL CONTENT: Does the message discuss the specific legal doctrine, statute, regulation, or procedural rule that the question addresses?

2. PRACTICAL GUIDANCE: Does it provide real-world experience, strategic advice, or tactical recommendations relevant to the question?

3. AUTHORITATIVE REFERENCES: Does it cite applicable case law, Labor Code sections, WCAB decisions, regulations, or administrative directives that bear on the question?

4. PROCEDURAL CLARITY: If the question involves procedure, does the message explain the actual steps, timing, filing requirements, or jurisdictional issues?

5. DIRECT RESPONSIVENESS: Does the attorney appear to be directly answering this question or a materially identical question?

MARK AS RELEVANT (is_relevant: true) IF:
- The message directly addresses the legal issue raised in the question
- It provides a legal answer, analysis, or framework that resolves the question
- It discusses the same procedural mechanism, statute, or rule that the question concerns
- It contains practical attorney experience handling this exact scenario
- It cites binding or persuasive authority that answers the question

MARK AS NOT RELEVANT (is_relevant: false) IF:
- The message merely contains keywords but discusses an unrelated issue
- It's a tangential discussion that doesn't help answer the question
- The legal context is different (e.g., different benefit type, different procedural posture)
- It's administrative chatter, meeting announcements, or off-topic discussion

CONFIDENCE SCORING:
0.95-1.0: This message directly answers the question with legal authority or clear guidance
0.80-0.94: Highly relevant - discusses the exact issue with substantive analysis
0.60-0.79: Relevant - provides useful related information that partially addresses the question
0.40-0.59: Marginally relevant - touches on related concepts but doesn't answer the question
0.00-0.39: Not relevant - different topic or only superficial keyword overlap

Respond in JSON format:
{{
  "is_relevant": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Explain specifically what legal information this message provides (or fails to provide) in relation to the user's question"
}}
"""
        return prompt
    
    def _parse_response(self, response) -> Dict:
        """Parse OpenAI response"""
        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            
            return {
                'is_relevant': bool(data.get('is_relevant', False)),
                'confidence': float(data.get('confidence', 0.0)),
                'reasoning': str(data.get('reasoning', 'No reasoning provided'))
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"⚠️  Error parsing AI response: {e}")
            return {
                'is_relevant': False,
                'confidence': 0.0,
                'reasoning': 'Failed to parse AI response'
            }
    
    def _calculate_cost(self, tokens: int, model: str) -> float:
        """
        Calculate cost based on tokens and model
        
        Pricing (as of 2024):
        - gpt-4o: $5.00/1M input, $15.00/1M output
        - gpt-4o-mini: $0.15/1M input, $0.60/1M output
        - gpt-3.5-turbo: $0.50/1M input, $1.50/1M output
        """
        
        # Simplified calculation (assumes 50/50 input/output split)
        cost_per_1k = {
            'gpt-4o': 0.010,  # $10/1M average
            'gpt-4o-mini': 0.000375,  # $0.375/1M average
            'gpt-3.5-turbo': 0.001  # $1/1M average
        }
        
        rate = cost_per_1k.get(model, 0.001)  # Default to gpt-3.5-turbo rate
        return (tokens / 1000) * rate
    
    def get_usage_stats(self) -> Dict:
        """Get cumulative usage statistics"""
        return {
            'total_tokens': self.total_tokens_used,
            'total_cost_usd': round(self.total_cost_usd, 4),
            'model': self.model
        }


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Example: Test AI analyzer
    
    # You need to set OPENAI_API_KEY environment variable
    # or pass api_key="your-key" to AIAnalyzer()
    
    try:
        analyzer = AIAnalyzer(model="gpt-4o-mini")
        
        # Test message 1: Clearly relevant
        message1 = {
            'subject': 'Question about permanent disability rates',
            'body': 'I have a client with 35% permanent disability. What are the current rates for calculating PD benefits in California workers compensation cases?',
            'from_name': 'John Smith'
        }
        
        result1 = analyzer.analyze_relevance(message1, "workers compensation")
        print("Test 1: Clearly relevant message")
        print(f"  Relevant: {result1['is_relevant']}")
        print(f"  Confidence: {result1['confidence']}")
        print(f"  Reasoning: {result1['reasoning']}")
        print(f"  Cost: ${result1['cost_usd']:.6f}")
        print()
        
        # Test message 2: Not relevant
        message2 = {
            'subject': 'Office closing early today',
            'body': 'Just a reminder that the office will close at 3pm today for the holiday weekend.',
            'from_name': 'Office Manager'
        }
        
        result2 = analyzer.analyze_relevance(message2, "workers compensation")
        print("Test 2: Not relevant message")
        print(f"  Relevant: {result2['is_relevant']}")
        print(f"  Confidence: {result2['confidence']}")
        print(f"  Reasoning: {result2['reasoning']}")
        print(f"  Cost: ${result2['cost_usd']:.6f}")
        print()
        
        # Show usage stats
        stats = analyzer.get_usage_stats()
        print(f"Total usage:")
        print(f"  Tokens: {stats['total_tokens']}")
        print(f"  Cost: ${stats['total_cost_usd']:.6f}")
        
    except ValueError as e:
        print(f"Error: {e}")
        print("\nTo test, set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-key-here'")

