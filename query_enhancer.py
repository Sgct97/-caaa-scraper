#!/usr/bin/env python3
"""
Query Enhancer - AI Layer 1
Converts plain English user queries into optimized SearchParams
"""

import os
import json
import openai
from typing import Dict, Optional
from datetime import date, timedelta
import re

from search_params import SearchParams


class QueryEnhancer:
    """Uses AI to translate plain English queries into search parameters"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize query enhancer
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4o-mini)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter.")
        
        openai.api_key = self.api_key
        self.model = model
    
    def enhance_query(self, user_query: str) -> SearchParams:
        """
        Convert plain English query into optimized SearchParams
        
        Args:
            user_query: Plain English description of what user wants to find
            
        Returns:
            SearchParams object optimized for CAAA search
        """
        
        print(f"\n{'='*60}")
        print("AI QUERY ENHANCEMENT")
        print(f"{'='*60}")
        print(f"User query: \"{user_query}\"")
        print("\n→ Asking AI to optimize search parameters...")
        
        # Build prompt
        prompt = self._build_enhancement_prompt(user_query)
        
        try:
            # Call OpenAI
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at California workers' compensation law and legal research. Your job is to translate plain English queries into optimized search parameters for a legal listserv database."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=800
            )
            
            # Parse response
            result = self._parse_ai_response(response)
            
            # Convert to SearchParams
            search_params = self._create_search_params(result)
            
            print("\n✓ AI-optimized search parameters:")
            print(f"  {search_params}")
            
            return search_params
            
        except Exception as e:
            print(f"\n❌ Error enhancing query: {e}")
            print("→ Falling back to simple keyword search")
            
            # Fallback: use user query as simple keyword
            return SearchParams(keyword=user_query)
    
    def _build_enhancement_prompt(self, user_query: str) -> str:
        """Build the prompt for OpenAI"""
        
        prompt = f"""The user wants to search a California workers' compensation legal listserv.

USER QUERY: "{user_query}"

Your task: Analyze this query and determine the BEST search parameters to find relevant messages.

Available search fields:
1. keyword - Simple keyword search (searches subject + body)
2. keywords_all - Must contain ALL these keywords (space-separated)
3. keywords_phrase - Exact phrase match
4. keywords_any - Must contain at least ONE of these (space-separated)
5. keywords_exclude - Must NOT contain these keywords
6. listserv - Which list: "all", "lawnet", "lavaaa", "lamaaa", "scaaa"
   - lawnet: Applicant attorneys (workers' side)
   - lavaaa: Defense attorneys (employer/insurance side)
7. date_from - Start date (YYYY-MM-DD)
8. date_to - End date (YYYY-MM-DD)
9. search_in - "subject_and_body" or "subject_only"

Guidelines:
- Use keywords_all for concepts that must appear together
- Use keywords_any for synonyms or related terms
- Use keywords_phrase for legal terms that should appear exactly
- Infer date ranges from temporal phrases ("last 3 months", "recent", etc.)
- Choose appropriate listserv if context suggests worker vs employer side
- Think about legal synonyms and abbreviations (PD = permanent disability, TD = temporary disability, etc.)

Respond in JSON format:
{{
  "reasoning": "Brief explanation of search strategy",
  "parameters": {{
    "keyword": "string or null",
    "keywords_all": "string or null",
    "keywords_phrase": "string or null",
    "keywords_any": "string or null",
    "keywords_exclude": "string or null",
    "listserv": "all/lawnet/lavaaa/lamaaa/scaaa",
    "date_from": "YYYY-MM-DD or null",
    "date_to": "YYYY-MM-DD or null",
    "search_in": "subject_and_body or subject_only"
  }}
}}
"""
        return prompt
    
    def _parse_ai_response(self, response) -> Dict:
        """Parse OpenAI response"""
        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            
            print(f"\n→ AI reasoning: {data.get('reasoning', 'No reasoning provided')}")
            
            return data.get('parameters', {})
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"⚠️  Error parsing AI response: {e}")
            return {}
    
    def _create_search_params(self, ai_params: Dict) -> SearchParams:
        """Convert AI parameters to SearchParams object"""
        
        # Parse date strings
        date_from = None
        date_to = None
        
        if ai_params.get('date_from'):
            try:
                date_from = date.fromisoformat(ai_params['date_from'])
            except:
                pass
        
        if ai_params.get('date_to'):
            try:
                date_to = date.fromisoformat(ai_params['date_to'])
            except:
                pass
        
        # Create SearchParams
        return SearchParams(
            keyword=ai_params.get('keyword'),
            keywords_all=ai_params.get('keywords_all'),
            keywords_phrase=ai_params.get('keywords_phrase'),
            keywords_any=ai_params.get('keywords_any'),
            keywords_exclude=ai_params.get('keywords_exclude'),
            listserv=ai_params.get('listserv', 'all'),
            date_from=date_from,
            date_to=date_to,
            search_in='subject_only' if ai_params.get('search_in') == 'subject_only' else 'subject_and_body',
            max_pages=10,
            max_messages=100
        )


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Test queries
    test_queries = [
        "I need cases about injured workers getting denied medical treatment in the last 3 months",
        "Recent discussions about permanent disability ratings",
        "What are attorneys saying about SIBTF applications?",
        "Find messages about depositions for psychiatric evaluations",
        "Any posts about LC 5710 attorney fees from this year?"
    ]
    
    try:
        enhancer = QueryEnhancer(model="gpt-4o-mini")
        
        for query in test_queries:
            print("\n" + "="*60)
            search_params = enhancer.enhance_query(query)
            print(f"\nGenerated form data:")
            print(json.dumps(search_params.to_form_data(), indent=2))
            
            input("\nPress ENTER for next test...\n")
        
    except ValueError as e:
        print(f"Error: {e}")
        print("\nTo test, set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-key-here'")

