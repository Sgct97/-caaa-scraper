#!/usr/bin/env python3
"""
AI Analyzer Module
Uses OpenAI to determine if messages are relevant to search queries
"""

import os
from typing import Dict, Optional
import json
import anthropic
import re as regex


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
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
    
    def analyze_relevance(self, 
                         message: Dict[str, str],
                         real_question: str,
                         search_keyword: str,
                         additional_context: Optional[str] = None) -> Dict:
        """
        Analyze if a message is relevant to the REAL question
        
        Args:
            message: Dict with keys: subject, body, from_name
            real_question: The user's REAL question (what they actually want to know)
            search_keyword: The search keywords/parameters used (for context)
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
        prompt = self._build_prompt(message, real_question, search_keyword, additional_context)
        
        try:
            # Call OpenAI
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                system="You are an expert legal assistant. Always respond with valid JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            result = self._parse_response(response)
            
            # Track usage
            tokens_used = (response.usage.input_tokens + response.usage.output_tokens)
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
    
    def _build_prompt(self, message: Dict, real_question: str, search_keyword: str, context: Optional[str]) -> str:
        """Build the prompt for OpenAI"""
        
        subject = message.get('subject', 'No subject')
        body = message.get('body', '')
        from_name = message.get('from_name', 'Unknown')
        
        # Truncate body if too long (to save tokens)
        max_body_length = 2000
        if len(body) > max_body_length:
            body = body[:max_body_length] + "... [truncated]"
        
        prompt = f"""You are the Relevance Analyzer in a 3-part legal research system:

SYSTEM OVERVIEW:
1. Vagueness Checker → Identified the REAL question
2. Query Enhancer → Generated search parameters based on REAL question
3. YOU (Relevance Analyzer) → Determine if each message answers the REAL question

YOUR SPECIFIC ROLE:
You are an expert California workers' compensation attorney analyzing listserv messages from CAAA (California Applicants' Attorneys Association). Your job is to determine if each message provides substantive information that helps answer the user's REAL legal question.

THE REAL QUESTION:
"{real_question}"

🚨 CRITICAL: This is the user's REAL question - what they actually want to know. Your entire analysis must focus on whether this message helps answer THIS REAL question. The REAL question may differ from the search keywords used below.

SEARCH KEYWORDS USED:
"{search_keyword}"

(These are the search parameters that were used to find this message. They are provided ONLY for context about how the message was found. DO NOT reference these keywords in your reasoning. Your reasoning must reference the REAL question above, not these search keywords.)

CONTEXT:
This message is from a professional legal discussion forum where experienced workers' compensation attorneys discuss case strategies, statutory interpretations, procedural questions, and share practical insights from their practice.

MESSAGE TO ANALYZE:
From: {from_name}
Subject: {subject}

{body}

YOUR GOAL:
Determine if this message helps answer the REAL question. Consider:
- Does it provide actionable legal insight related to the REAL question?
- Does it cite relevant authorities  that addresses the REAL question?
- Does it offer practical guidance that addresses the REAL question?
- Does it discuss the specific legal issue, procedure, or concept from the REAL question?

🚨 CRITICAL INSTRUCTION FOR REASONING:
When writing your reasoning, you MUST reference the REAL question (e.g., "This message helps answer the user's question about [REAL question]"). DO NOT reference the search keywords in your reasoning. The search keywords are just technical parameters used to find messages - they are NOT what the user is asking about.

SPECIAL CASE - AUTHOR-FOCUSED SEARCHES:
IF the REAL question is asking for messages FROM or MENTIONING a specific person (e.g., "messages from Ray Saedi", "posts by John Smith"), then:
- Mark as RELEVANT if the message is FROM that person OR clearly MENTIONS them
- Set confidence to 0.95 if from that person, 0.85 if mentioning them
- Reasoning: Simply state "Message from [name]" or "Message mentions [name]"
- DO NOT judge content quality - if it's from/mentions the person, it's relevant

CONFIDENCE SCORING:
0.95-1.0: Directly answers the REAL question with legal authority or clear guidance
0.80-0.94: Highly relevant - discusses the exact issue with substantive analysis
0.60-0.79: Relevant - provides useful related information that partially addresses the REAL question
0.40-0.59: Marginally relevant - touches on related concepts but doesn't answer the REAL question
0.00-0.39: Not relevant - different topic or only superficial keyword overlap

Return JSON:
{{
  "is_relevant": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Explain how this message relates to (or fails to relate to) the REAL question above. Reference the REAL question in your reasoning, NOT the search keywords."
}}"""
        return prompt
    
    def _parse_response(self, response) -> Dict:
        """Parse OpenAI response"""
        try:
            raw = response.content[0].text; import re; match = re.search(r"{[sS]*}", raw); content = match.group() if match else raw
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
    
    def synthesize_doctor_evaluation(self, doctor_name: str, messages: list[Dict]) -> Dict:
        """
        Synthesize all messages about a doctor to determine if they are "good" or "bad"
        from a California workers' compensation attorney's perspective.
        
        Args:
            doctor_name: Name of the doctor being evaluated
            messages: List of message dicts with keys: subject, body, from_name, etc.
        
        Returns:
            Dict with:
                - score: int (0-100) - Overall quality score
                - evaluation: str ("good", "bad", or "mixed")
                - reasoning: str - Detailed explanation
                - cost_usd: float - API cost
        """
        if not messages:
            return {
                'score': 0,
                'evaluation': 'unknown',
                'reasoning': 'No messages found about this doctor.',
                'cost_usd': 0.0
            }
        
        prompt = self._build_synthesis_prompt(doctor_name, messages)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system="You are an expert California workers' compensation attorney evaluating medical experts.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            response_text = response.content[0].text
            
            # Extract JSON from response
            json_match = regex.search(r'\{.*\}', response_text, regex.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Fallback parsing
                result = {
                    'score': 50,
                    'evaluation': 'mixed',
                    'reasoning': response_text
                }
            
            # Validate and normalize score
            score = int(result.get('score', 50))
            score = max(0, min(100, score))  # Clamp to 0-100
            
            evaluation = result.get('evaluation', 'mixed').lower()
            if evaluation not in ['good', 'bad', 'mixed']:
                evaluation = 'mixed'
            
            # Track usage
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            self.total_tokens_used += tokens_used
            cost = self._calculate_cost(tokens_used, self.model)
            self.total_cost_usd += cost
            
            return {
                'score': score,
                'evaluation': evaluation,
                'reasoning': result.get('reasoning', response_text),
                'cost_usd': cost
            }
            
        except Exception as e:
            print(f"⚠️  Synthesis error: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return {
                'score': 50,
                'evaluation': 'error',
                'reasoning': f'Error during synthesis: {str(e)}',
                'cost_usd': 0.0
            }
    
    def _build_synthesis_prompt(self, doctor_name: str, messages: list[Dict]) -> str:
        """Build the synthesis prompt for doctor evaluation"""
        
        # Format messages for prompt
        messages_text = ""
        for i, msg in enumerate(messages[:50], 1):  # Limit to 50 messages to avoid token limits
            messages_text += f"\n--- Message {i} ---\n"
            messages_text += f"From: {msg.get('from_name', 'Unknown')}\n"
            messages_text += f"Subject: {msg.get('subject', 'No subject')}\n"
            messages_text += f"Body: {msg.get('body', '')[:1000]}\n"  # Limit body length
        
        prompt = f"""You are an expert California workers' compensation attorney evaluating a medical expert/doctor based on discussions from a professional legal listserv.

DOCTOR BEING EVALUATED: {doctor_name}

You have access to {len(messages)} messages from experienced California workers' compensation attorneys discussing this doctor. Your job is to synthesize ALL of these messages to determine:

1. Is this doctor "good" or "bad" from an attorney's perspective?
2. What is their overall quality score (0-100)?
3. What are the key factors attorneys mention?

EVALUATION CRITERIA (from attorney perspective):
- Quality of medical reports (thoroughness, accuracy, clarity)
- Consistency with legal standards and regulations
- Responsiveness to attorney requests
- Credibility and reliability
- Patterns of positive vs negative experiences
- Any red flags or concerns mentioned
- Overall reputation among attorneys

MESSAGES TO ANALYZE:
{messages_text}

YOUR TASK:
Synthesize ALL messages to provide a comprehensive evaluation. Consider:
- What patterns emerge across multiple messages?
- Are there consistent positive or negative themes?
- What specific strengths or weaknesses are mentioned?
- How do attorneys generally view this doctor?

Return JSON:
{{
  "score": <0-100 integer>,
  "evaluation": "good" | "bad" | "mixed",
  "reasoning": "<detailed explanation of your evaluation, citing specific examples from the messages>"
}}

SCORING GUIDE:
- 80-100: Excellent doctor, highly recommended by attorneys
- 60-79: Good doctor with some positive feedback
- 40-59: Mixed reviews, some concerns
- 20-39: Generally negative feedback, significant concerns
- 0-19: Poor doctor, multiple red flags, not recommended

Be thorough and cite specific examples from the messages in your reasoning."""
        
        return prompt
    
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
        
        result1 = analyzer.analyze_relevance(message1, "workers compensation", "workers compensation")
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
        
        result2 = analyzer.analyze_relevance(message2, "workers compensation", "workers compensation")
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

