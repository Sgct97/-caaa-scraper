#!/usr/bin/env python3
"""
Query Enhancer - AI Layer 1
Converts plain English user queries into optimized SearchParams
"""

import os
import json
import anthropic
import re as regex
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
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
    
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
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                system="You are an expert at California workers' compensation law and legal research. Your job is to translate plain English queries into optimized search parameters for a legal listserv database. Always respond with valid JSON.",
                messages=[{"role": "user", "content": prompt}]
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
        
        prompt = f"""You are the Query Enhancer in a 3-part legal research system:

SYSTEM OVERVIEW:
1. Vagueness Checker → Already identified the REAL question (either from original query or after follow-ups)
2. YOU (Query Enhancer) → Translate the REAL question into optimized search parameters
3. Relevance Analyzer → Will score messages using your parameters to see if they answer the REAL question

YOUR SPECIFIC ROLE:
You are an expert California workers' compensation attorney and legal research specialist. The Vagueness Checker has already ensured we have the user's REAL legal question. Your job is to translate that REAL question into search parameters that will retrieve the most relevant messages from a CAAA listserv database.

THE REAL QUESTION:
"{user_query}"

(This is the user's REAL question - either it was clear from the start, or the Vagueness Checker asked follow-ups to clarify it. Your job is to translate THIS question into search parameters.)

YOUR GOAL:
Generate search parameters that maximize the chance that:
- The scraper finds messages relevant to the REAL question
- The Relevance Analyzer can identify which messages actually answer the REAL question
- The user gets actionable legal information

AVAILABLE SEARCH FIELDS:
1. posted_by - Filter by WHO SENT the message (e.g., "messages BY Ray Saedi" → "Ray Saedi")
2. author_first_name + author_last_name - For WITNESS/EXPERT searches (QMEs, doctors, medical experts)
3. keyword - Simple keyword search (searches subject + body)
4. keywords_all - Must contain ALL these keywords (comma-separated) - Use for narrow searches
5. keywords_phrase - Exact phrase match - Avoid unless explicitly requested
6. keywords_any - Must contain at least ONE of these (comma-separated) - PRIMARY TOOL for broad searches
7. keywords_exclude - Must NOT contain these keywords (comma-separated)
8. listserv - Which list: "all", "lawnet", "lavaaa", "lamaaa", "scaaa"
9. attachment_filter - "all", "with_attachments", "without_attachments"
10. date_from - Start date (YYYY-MM-DD) - Use for temporal queries ("recent" = 6 months ago)
11. date_to - End date (YYYY-MM-DD) - Only for specific date ranges
12. search_in - "subject_and_body" or "subject_only"

SEARCH STRATEGY PRINCIPLES:
- keywords_any = BROAD search → Use when you want comprehensive results (PRIMARY TOOL)
- keywords_all = NARROW search → Use when multiple concepts MUST co-occur
- Person names: Distinguish WHO SENT (posted_by) vs EXPERT MENTIONED (author_first_name/author_last_name)
- Temporal keywords ("recent", "latest", "new") → Use date_from filter
- Think about synonyms, abbreviations (QME, IMR, LC, PD), and related legal concepts

TODAY'S DATE: {today.strftime('%Y-%m-%d')}

HOW TO TRANSLATE THE REAL QUESTION INTO SEARCH PARAMETERS:
1. **Identify the core legal concepts** in the REAL question - what is the user actually trying to learn?
2. **Think about how attorneys would discuss this** - what terms, phrases, or case names would appear in relevant messages?
3. **Consider the search field that best captures the intent** - is this about a person (posted_by/author fields), a topic (keywords), a time period (date filters), or a combination?
4. **Optimize for recall** - Use keywords_any (broad) rather than keywords_all (narrow) unless the REAL question requires multiple concepts together
5. **Include synonyms and related terms** - Think about how the same concept might be expressed differently (e.g., "permanent disability" vs "PD" vs "impairment rating")
6. **Use temporal filters when appropriate** - If the REAL question asks about "recent" or "latest" information, apply date filters
7. **Consider the listserv context** - If the REAL question is about applicant-side or defense-side perspectives, filter by listserv

Translate the REAL question into the best possible search parameters optimized for finding answers. Your parameters should maximize the likelihood that the scraper finds messages that actually help answer the REAL question. Return JSON:
{{
  "reasoning": "How these parameters help find answers to the REAL question",
  "parameters": {{
    "keyword": "string or null",
    "keywords_all": "comma-separated terms or null",
    "keywords_phrase": null,
    "keywords_any": "comma-separated terms or null",
    "keywords_exclude": "comma-separated terms or null",
    "listserv": "all/lawnet/lavaaa/lamaaa/scaaa",
    "author_first_name": "first name or null",
    "author_last_name": "last name or null",
    "posted_by": "FULL NAME or null",
    "attachment_filter": "all/with_attachments/without_attachments",
    "date_from": "YYYY-MM-DD or null",
    "date_to": "YYYY-MM-DD or null",
    "search_in": "subject_and_body or subject_only"
  }}
}}"""
        return prompt
    
    def _parse_ai_response(self, response) -> Dict:
        """Parse OpenAI response"""
        try:
            raw = response.content[0].text
            # Extract JSON from response
            match = regex.search(r"\{[\s\S]*\}", raw)
            content = match.group() if match else raw
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
    # DETERMINISTIC QUERY ENHANCERS (No AI calls)
    # For person-name searches where consistency is critical
    # ============================================================
    
    def _extract_name(self, raw_name: str, prefixes: list) -> tuple:
        """
        Extract clean name from input, removing professional prefixes.
        
        Args:
            raw_name: Raw input like "Judge Dobrin" or "Hon. John Smith"
            prefixes: List of prefixes to strip (case-insensitive)
            
        Returns:
            tuple: (full_clean_name, last_name_only)
        """
        name = raw_name.strip()
        
        # Remove common prefixes (case-insensitive)
        for prefix in prefixes:
            # Handle prefixes with or without periods/spaces
            pattern = re.compile(rf'^{re.escape(prefix)}[\s.]*', re.IGNORECASE)
            name = pattern.sub('', name).strip()
        
        # Split into parts
        parts = name.split()
        
        if len(parts) >= 2:
            # Full name provided (e.g., "John Dobrin")
            full_name = name
            last_name = parts[-1]  # Last word is last name
        else:
            # Single name provided (e.g., "Dobrin")
            full_name = name
            last_name = name
        
        return (full_name, last_name)
    
    def enhance_judge_query(self, name: str) -> SearchParams:
        """
        Deterministic query enhancement for judge searches.
        
        Generates consistent, exhaustive variations of judge name
        to maximize search recall without AI variability.
        
        Args:
            name: Judge name (e.g., "Dobrin", "Judge Dobrin", "John Dobrin")
            
        Returns:
            SearchParams with keywords_any containing all variations
        """
        # Common judge-related prefixes to strip
        judge_prefixes = [
            "Judge", "Hon.", "Hon", "Honorable", "WCJ", 
            "Workers Compensation Judge", "Workers' Compensation Judge"
        ]
        
        full_name, last_name = self._extract_name(name, judge_prefixes)
        
        # Build variations list
        variations = []
        
        # Last name variations (always include)
        variations.extend([
            f"Judge {last_name}",
            last_name,
            f"Hon. {last_name}",
            f"Hon {last_name}",
            f"WCJ {last_name}",
            f"Honorable {last_name}",
            f"{last_name} WCJ",
        ])
        
        # If full name differs from last name, add full name variations too
        if full_name != last_name:
            variations.extend([
                f"Judge {full_name}",
                full_name,
                f"Hon. {full_name}",
                f"WCJ {full_name}",
                f"Honorable {full_name}",
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            if v.lower() not in seen:
                seen.add(v.lower())
                unique_variations.append(v)
        
        keywords_any = ", ".join(unique_variations)
        
        print(f"\n{'='*60}")
        print("DETERMINISTIC JUDGE QUERY ENHANCEMENT")
        print(f"{'='*60}")
        print(f"Input: \"{name}\"")
        print(f"Extracted: full_name=\"{full_name}\", last_name=\"{last_name}\"")
        print(f"Generated {len(unique_variations)} search variations:")
        for v in unique_variations:
            print(f"  • {v}")
        print(f"keywords_any: \"{keywords_any}\"")
        
        return SearchParams(
            keywords_any=keywords_any,
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

