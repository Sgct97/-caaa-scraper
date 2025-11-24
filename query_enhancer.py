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
- If YES: Extract the LAST NAME ONLY and use author_last_name field
- EXAMPLES: 
  ✓ "Chris Johnson" → author_last_name: "Johnson"
  ✓ "articles mentioning Chris Johnson" → author_last_name: "Johnson"
  ✓ "what did John Smith say" → author_last_name: "Smith"
  ✗ NEVER put person names in keywords - ONLY use author_last_name

TODAY'S DATE: {today.strftime('%Y-%m-%d')}

Your task: Analyze this query and determine the BEST search parameters to find relevant messages.

Available search fields:
1. author_last_name - 🚨 USE THIS FOR PERSON NAMES! Extract last name only (e.g., "Chris Johnson" → "Johnson")
2. author_first_name - Author's first name (optional, use with last name)
3. posted_by - Filter by poster email or name
4. keyword - Simple keyword search (searches subject + body)
5. keywords_all - Must contain ALL these keywords (comma-separated: "word1, word2, word3")
6. keywords_phrase - Exact phrase match (e.g., "permanent disability rating")
7. keywords_any - Must contain at least ONE of these (comma-separated: "term1, term2, term3")
8. keywords_exclude - Must NOT contain these keywords (comma-separated)
9. listserv - Which list: "all", "lawnet", "lavaaa", "lamaaa", "scaaa"
   - lawnet: Applicant attorneys (workers' side)
   - lavaaa: Defense attorneys (employer/insurance side)
10. attachment_filter - "all", "with_attachments", "without_attachments"
11. date_from - Start date (YYYY-MM-DD)
12. date_to - End date (YYYY-MM-DD)
13. search_in - "subject_and_body" or "subject_only"

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
- **USE keywords_exclude to filter OUT unwanted topics** - very powerful for narrowing results
- For general queries about a topic, use keywords_any with relevant terms and synonyms

EXAMPLES:
1. "Paterson case changes" → keywords_any: "Paterson, amended, modified, overturned, changed, reversed"
2. "recent changes to Paterson" → keywords_any: "Paterson, amended, modified, changed, reversed" AND date_from: 6 months ago, date_to: null
3. "recent articles mentioning Chris Johnson" → author_last_name: "Johnson" AND date_from: 6 months ago, date_to: null (NO keywords)
4. "What did Judge Smith say about apportionment?" → keywords_any: "apportionment" AND author_last_name: "Smith"
5. "IMR appeal process" → keywords_any: "IMR, appeal, review, decision, WCAB"
6. "QME issues but not apportionment" → keywords_any: "QME" AND keywords_exclude: "apportionment"
7. "permanent disability excluding psych cases" → keywords_any: "permanent disability, PD" AND keywords_exclude: "psychiatric, psychological, psych"
8. "articles from applicant attorneys about LC 4663" → keywords_any: "LC 4663, Labor Code 4663" AND listserv: "lawnet"
9. "defense attorney discussions on utilization review" → keywords_any: "utilization review, UR" AND listserv: "lavaaa"
10. "posts with attachments about IMR" → keywords_any: "IMR" AND attachment_filter: "with_attachments"

- **DO NOT USE keywords_phrase UNLESS EXPLICITLY TOLD TO** - exact phrases almost always return 0 results
- **NEVER create exact phrases on your own** - only use them if the user explicitly requests an exact phrase match
- **USE DATE FILTERS when user asks about temporal context:**
  - "recent" / "latest" / "new" → date_from = 6 months ago, date_to = null (NEVER set date_to for "recent")
  - "current year" / "this year" → date_from = start of current year, date_to = null
  - "last year" → date_from and date_to for previous year ONLY
  - Specific dates or ranges → use exact dates
  - If NO temporal keywords, leave BOTH date_from and date_to as null
  - CRITICAL: For "recent", ONLY set date_from, NEVER set date_to
- **RECOGNIZE NAMES and use author filters (CRITICAL FOR RELEVANCE):**
  - If query mentions a PERSON'S NAME in any context (articles mentioning X, posts by X, what X said, etc.), use author_last_name field
  - Patterns: "articles mentioning X", "posts by X", "X wrote", "according to X", "X discussed", "X's opinion"
  - Extract the LAST NAME ONLY (e.g., "Chris Johnson" → author_last_name: "Johnson", NOT keywords)
  - DO NOT put person names in keywords_any - use author_last_name field instead
  - Example: "recent articles mentioning Chris Johnson" → author_last_name: "Johnson" AND date_from: 6 months ago (NO keywords needed)
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
1. IF QUERY MENTIONS A PERSON'S NAME (e.g., "Chris Johnson", "John Smith"), ALWAYS use author_last_name field with LAST NAME ONLY
2. ALWAYS use commas between different keywords in keywords_all, keywords_any, and keywords_exclude
3. DO NOT use keywords_phrase - set it to null
4. PREFER keywords_any over keywords_all for broader, more useful results
5. For "recent" queries, set date_from to 6 months ago and leave date_to as null
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

