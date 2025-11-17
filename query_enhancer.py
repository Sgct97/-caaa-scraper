#!/usr/bin/env python3
"""
Query Enhancer - AI Layer 1
Converts plain English user queries into optimized SearchParams
"""

import os
import json
from openai import OpenAI
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
        # Use Vast.ai GPU with Qwen 32B via SSH tunnel for fast, HIPAA-compliant processing
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
        self.client = OpenAI(
            base_url=ollama_url,
            api_key="ollama"
        )
        self.model = "qwen2.5:32b"
    
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
            response = self.client.chat.completions.create(
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
                temperature=0.0,
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
        
        # Get current date for relative date calculations
        today = date.today()
        
        prompt = f"""The user wants to search a California workers' compensation legal listserv.

TODAY'S DATE: {today.strftime('%Y-%m-%d')}

USER QUERY: "{user_query}"

Your task: Analyze this query and determine the BEST search parameters to find relevant messages.

Available search fields:
1. keyword - Simple keyword search (searches subject + body)
2. keywords_all - Must contain ALL these keywords (comma-separated: "word1, word2, word3")
3. keywords_phrase - Exact phrase match (e.g., "permanent disability rating")
4. keywords_any - Must contain at least ONE of these (comma-separated: "term1, term2, term3")
5. keywords_exclude - Must NOT contain these keywords (comma-separated)
6. listserv - Which list: "all", "lawnet", "lavaaa", "lamaaa", "scaaa"
   - lawnet: Applicant attorneys (workers' side)
   - lavaaa: Defense attorneys (employer/insurance side)
7. date_from - Start date (YYYY-MM-DD)
8. date_to - End date (YYYY-MM-DD)
9. search_in - "subject_and_body" or "subject_only"

CRITICAL FORMATTING RULES - MUST FOLLOW:
- For keywords_all, keywords_any, keywords_exclude: ALWAYS USE COMMAS to separate each term
- CORRECT: "expedited, hearing, IMR, appeal"
- WRONG: "expedited hearing IMR appeal" (NO SPACES WITHOUT COMMAS)
- WRONG: "expedited vs regular hearing" (NO connecting words like "vs", "or", "and")
- Each term should be a single word or short phrase, separated by commas
- If you want "IMR appeal" as one term, write it as one: "IMR appeal, expedited, hearing"
- ALWAYS put commas between different concepts

Guidelines:
- **USE keywords_any AS YOUR PRIMARY TOOL** - this finds messages containing ANY of the important terms (broadest results)
- Use keywords_all ONLY when you need messages that contain MULTIPLE SPECIFIC terms together (narrow, focused searches)
- For general queries about a topic, use keywords_any with relevant terms and synonyms
- Example: "Paterson case changes" → keywords_any: "Paterson, amended, modified, overturned, changed, reversed"
- Example: "recent changes to Paterson" → keywords_any: "Paterson, amended, modified, changed, reversed" AND date_from: 6 months ago
- Example: "IMR appeal process" → keywords_any: "IMR, appeal, review, decision, WCAB"
- **DO NOT USE keywords_phrase UNLESS EXPLICITLY TOLD TO** - exact phrases almost always return 0 results
- **NEVER create exact phrases on your own** - only use them if the user explicitly requests an exact phrase match
- **USE DATE FILTERS when user asks about temporal context:**
  - "recent" / "latest" / "new" → date_from = 6 months ago (this is CRITICAL for relevance)
  - "current year" / "this year" → date_from = start of current year
  - "last year" → date_from and date_to for previous year
  - Specific dates or ranges → use exact dates
  - If NO temporal keywords, leave date filters null
- Choose appropriate listserv if context suggests worker vs employer side
- Think about legal synonyms and abbreviations (PD = permanent disability, TD = temporary disability, etc.)

Respond in JSON format:
{{
  "reasoning": "Brief explanation of search strategy",
  "parameters": {{
    "keyword": "string or null",
    "keywords_all": "comma-separated terms or null (ONLY for narrow searches requiring ALL terms together)",
    "keywords_phrase": null (LEAVE THIS NULL - do not use exact phrases unless explicitly requested),
    "keywords_any": "comma-separated terms or null (PRIMARY TOOL - EXAMPLE: \"Paterson, amended, modified, changed, reversed\")",
    "keywords_exclude": "comma-separated terms or null",
    "listserv": "all/lawnet/lavaaa/lamaaa/scaaa",
    "date_from": "YYYY-MM-DD or null",
    "date_to": "YYYY-MM-DD or null",
    "search_in": "subject_and_body or subject_only"
  }}
}}

CRITICAL RULES:
1. ALWAYS use commas between different keywords in keywords_all, keywords_any, and keywords_exclude
2. DO NOT use keywords_phrase - set it to null
3. PREFER keywords_any over keywords_all for broader, more useful results
"""
        return prompt
    
    def _parse_ai_response(self, response) -> Dict:
        """Parse OpenAI response"""
        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            
            print(f"\n→ AI reasoning: {data.get('reasoning', 'No reasoning provided')}")
            
            params = data.get('parameters', {})
            
            # Validate that parameters is a dictionary, not a list
            if isinstance(params, list):
                print(f"⚠️  AI returned parameters as a list instead of a dictionary. Falling back.")
                return {}
            
            if not isinstance(params, dict):
                print(f"⚠️  AI returned invalid parameters type: {type(params)}. Falling back.")
                return {}
            
            return params
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"⚠️  Error parsing AI response: {e}")
            return {}
    
    def _create_search_params(self, ai_params: Dict) -> SearchParams:
        """Convert AI parameters to SearchParams object"""
        
        # Helper to ensure keyword fields are strings, not arrays
        def clean_keyword_field(value):
            if value is None:
                return None
            if isinstance(value, list):
                # AI returned an array - join with commas
                return ", ".join(str(v).strip() for v in value if v)
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return None
                # If AI returned space-separated words without commas, fix it
                # Check if there are multiple words but no commas
                if ' ' in value and ',' not in value:
                    # Split on spaces and rejoin with commas
                    return ", ".join(word.strip() for word in value.split() if word.strip())
                return value
            return str(value)
        
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
        
        # Create SearchParams - clean all keyword fields
        return SearchParams(
            keyword=clean_keyword_field(ai_params.get('keyword')),
            keywords_all=clean_keyword_field(ai_params.get('keywords_all')),
            keywords_phrase=clean_keyword_field(ai_params.get('keywords_phrase')),
            keywords_any=clean_keyword_field(ai_params.get('keywords_any')),
            keywords_exclude=clean_keyword_field(ai_params.get('keywords_exclude')),
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

