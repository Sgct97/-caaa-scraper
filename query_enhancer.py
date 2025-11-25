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
            print(f"\n🔍 DEBUG - author_last_name field: {search_params.author_last_name}")
            print(f"🔍 DEBUG - Raw AI params: {result}")
            
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
        
        # Detect potential person names (two capitalized words)
        name_pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'
        detected_names = re.findall(name_pattern, user_query)
        
        name_warning = ""
        if detected_names:
            name_warning = f"\n🚨🚨🚨 DETECTED PERSON NAME(S): {', '.join(detected_names)} 🚨🚨🚨\n→ YOU MUST USE author_last_name FIELD FOR: {', '.join([name.split()[-1] for name in detected_names])}\n"
        
        prompt = f"""🚨🚨🚨 RULE #1: PERSON NAMES 🚨🚨🚨
BEFORE DOING ANYTHING ELSE, CHECK IF THE QUERY MENTIONS A PERSON'S NAME.

USER QUERY: "{user_query}"{name_warning}

Does this query mention a person's name (like "Chris Johnson", "John Smith", "Judge Lee", etc.)?
- CRITICAL: Distinguish between WHO SENT the message vs WHO is DISCUSSED in it
- EXAMPLES: 
  ✓ "articles BY Chris Johnson" → posted_by: "Chris Johnson" (filter by sender - use FULL NAME)
  ✓ "articles MENTIONING Chris Johnson" → keywords_any: "Chris Johnson, Johnson" (search message content)
  ✓ "what did John Smith say" → posted_by: "John Smith" (filter by sender - use FULL NAME)
  ✓ "discussions ABOUT Judge Lee" → keywords_any: "Judge Lee, Lee" (search message content)
  ✓ "messages posted BY Ray Saedi" → posted_by: "Ray Saedi" (filter by sender - use FULL NAME)
  ✓ "articles by Johnson" → author_last_name: "Johnson" (only last name given)

TODAY'S DATE: {today.strftime('%Y-%m-%d')}

Your task: Analyze this query and determine the BEST search parameters to find relevant messages.

Available search fields:
1. posted_by - 🚨 USE FOR FULL NAMES! Filter by WHO SENT the message (e.g., "articles BY Ray Saedi" → "Ray Saedi")
2. author_last_name - Filter by last name ONLY if no first name given (e.g., "articles BY Johnson" → "Johnson")
3. keyword - Simple keyword search (searches subject + body)
4. keywords_all - Must contain ALL these keywords (comma-separated: "word1, word2, word3")
5. keywords_phrase - Exact phrase match (e.g., "permanent disability rating")
6. keywords_any - Must contain at least ONE of these (comma-separated: "term1, term2, term3")
7. keywords_exclude - Must NOT contain these keywords (comma-separated)
8. listserv - Which list: "all", "lawnet", "lavaaa", "lamaaa", "scaaa"
   - lawnet: Applicant attorneys (workers' side)
   - lavaaa: Defense attorneys (employer/insurance side)
9. attachment_filter - "all", "with_attachments", "without_attachments"
10. date_from - Start date (YYYY-MM-DD)
11. date_to - End date (YYYY-MM-DD)
12. search_in - "subject_and_body" or "subject_only"

FORMATTING RULES:
- Multi-term fields (keywords_all, keywords_any, keywords_exclude) require COMMA separation
- Each distinct concept/synonym = separate comma-separated item
- Multi-word phrases can be one item: "labor code, workers compensation, permanent disability"
- NO connecting words (and/or/vs) - just commas: "term1, term2, term3"

SEARCH STRATEGY - Analyze the query and choose the RIGHT tool:

1. **Field Selection Principles:**
   - keywords_any = BROAD search (finds ANY matching term) → Use when you want comprehensive results
   - keywords_all = NARROW search (requires ALL terms) → Use when multiple concepts MUST co-occur
   - keywords_exclude = FILTER OUT unwanted results → Use when query explicitly excludes topics
   - keyword = SIMPLE search → Use for straightforward single-concept queries
   - keywords_phrase = EXACT MATCH → Avoid unless explicitly requested (returns few/no results)

2. **Person Names - Distinguish AUTHOR vs MENTIONED:**
   - "articles BY X" / "posts FROM X" / "what X said" / "X wrote" → posted_by with FULL NAME (filter by WHO SENT IT)
   - "articles MENTIONING X" / "discussions ABOUT X" / "references to X" → keywords_any (search IN message body)
   - 🚨 For author queries with full names: Use posted_by field
     * "posted by Ray Saedi" → posted_by: "Ray Saedi" (full name)
     * "articles by John Smith" → posted_by: "John Smith" (full name)
   - For "mentioning" queries, include full name or last name in keywords_any
   - Only use author_last_name if ONLY a last name is provided (e.g., "articles by Johnson")

3. **Temporal Keywords - USE DATE FILTERS:**
   - "recent"/"latest"/"new" → date_from = 6 months ago, date_to = null
   - "this year"/"current year" → date_from = start of year, date_to = null
   - Specific dates/ranges → use exact dates
   - NO temporal keywords → leave date fields null

4. **Negative Keywords - USE EXCLUSION:**
   - "but not X", "excluding X", "except X" → keywords_exclude
   - Be thoughtful about synonyms to exclude (e.g., excluding "psych" should also exclude "psychological", "psychiatric")

5. **Synonym Strategy:**
   - Think broadly about alternative terms, abbreviations, and related concepts
   - Legal context: consider abbreviations (LC = Labor Code, PD = permanent disability)
   - Use commas to separate all distinct terms

6. **Context Clues:**
   - "applicant attorney"/"worker's attorney" → listserv: "lawnet"
   - "defense attorney"/"employer attorney" → listserv: "lavaaa"
   - "with documents"/"attachments" → attachment_filter: "with_attachments"
   - "subject line only" → search_in: "subject_only"

CRITICAL: Your goal is to maximize recall (find all relevant messages) while maintaining precision (avoid irrelevant results). Choose fields that best balance these goals for the specific query.

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
    "author_first_name": "first name or null",
    "author_last_name": "last name only or null (use for person names - EXAMPLE: \"Johnson\")",
    "posted_by": "email or name or null",
    "attachment_filter": "all/with_attachments/without_attachments",
    "date_from": "YYYY-MM-DD or null (for 'recent' use 6 months ago)",
    "date_to": "YYYY-MM-DD or null (ONLY for specific date ranges, NOT for 'recent')",
    "search_in": "subject_and_body or subject_only"
  }}
}}

CRITICAL RULES:
1. Person names → ALWAYS use author_last_name (extract last name only)
2. Multi-term keyword fields → ALWAYS comma-separate
3. Avoid keywords_phrase unless explicitly requested
4. Balance recall vs precision based on query intent
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
            author_first_name=ai_params.get('author_first_name'),  # Author's first name
            author_last_name=ai_params.get('author_last_name'),  # 🚨 CRITICAL: Extract person names
            posted_by=ai_params.get('posted_by'),  # Posted by (email or name)
            attachment_filter=ai_params.get('attachment_filter', 'all'),  # with_attachments/without_attachments/all
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

