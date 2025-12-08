# Complete AI Prompts & Flow Documentation

## 🎯 **3 AI Prompts in the System**

---

## **PROMPT 1: Vagueness Check** (`app.py` lines 306-343)

**Location:** `/api/ai/analyze` endpoint  
**Purpose:** Determine if user query needs clarification BEFORE generating search parameters  
**Model:** Claude 4.5 Opus  
**Temperature:** Not specified (defaults to ~0.7)  
**Max Tokens:** 500

### When This Prompt Runs:
- **ALWAYS** runs first when user submits a query
- Runs BEFORE QueryEnhancer
- Decides: Ask follow-up OR proceed to QueryEnhancer

### The Prompt:
```python
vagueness_check = f"""Analyze this query and determine if it has enough information to search effectively.

Query: "{request.intent}"

A query is VAGUE if:
1. Multiple interpretations exist that would lead to VERY DIFFERENT searches
2. Key information is missing that would significantly change what we search for
3. The query is so broad that any search would return too many irrelevant results

A query is SPECIFIC if:
1. We can confidently determine what to search for
2. The search intent is unambiguous (or ambiguity doesn't matter much)
3. We have enough information to create targeted search parameters

CRITICAL DISTINCTIONS TO CHECK:
- Person name WITHOUT context → VAGUE (could mean BY them or ABOUT them)
  - "Chris Johnson" → VAGUE
  - "articles BY Chris Johnson" → SPECIFIC
  - "articles MENTIONING Chris Johnson" → SPECIFIC
  
- Topic without WHAT aspect → Often VAGUE
  - Just a case name → VAGUE (which aspect?)
  - "Case X's impact on Y" → SPECIFIC (clear aspect)
  
- Overly broad → May be VAGUE
  - "recent changes" → VAGUE (changes to what?)
  - "recent changes to settlement procedures" → SPECIFIC

When VAGUE, craft a clarifying question that:
1. Identifies the ambiguity/missing info
2. Offers 2-3 specific alternatives
3. Helps narrow the search effectively

Return JSON:
{
  "is_vague": true/false,
  "follow_up_question": "clarifying question" OR null
}"""
```

### Response Format:
```json
{
  "is_vague": false,
  "follow_up_question": null
}
```

OR

```json
{
  "is_vague": true,
  "follow_up_question": "What specific aspect of QME panel procedures are you looking for? For example: how to request a panel, procedural rules, or panel decision-making?"
}
```

### Code Flow:
```python
# app.py line 345-354
vagueness_response = orchestrator.client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=500,
    messages=[{"role": "user", "content": vagueness_check + " Respond with JSON only."}]
)

# Parse response
_raw = vagueness_response.content[0].text
_match = _re.search(r"\{[\s\S]*\}", _raw)
vagueness_result = json.loads(_match.group() if _match else _raw)

# If vague, return follow-up immediately (line 358-366)
if vagueness_result.get("is_vague", False):
    follow_up = vagueness_result.get("follow_up_question")
    return {
        "success": True,
        "analysis": "Query needs clarification",
        "suggestions": None,
        "follow_up_question": follow_up  # ← Frontend shows this to user
    }

# If specific, proceed to QueryEnhancer (line 368-373)
enhancer = QueryEnhancer()
search_params = enhancer.enhance_query(request.intent)
```

---

## **PROMPT 2: Query Enhancement** (`query_enhancer.py` lines 99-224)

**Location:** `QueryEnhancer.enhance_query()`  
**Purpose:** Convert plain English query → optimized SearchParams  
**Model:** Claude 4.5 Opus  
**Temperature:** Not specified (defaults to ~0.7)  
**Max Tokens:** 800

### When This Prompt Runs:
- **Path A:** If vagueness check says query is SPECIFIC → runs immediately
- **Path B:** After user answers follow-up → runs with refined query via `/api/ai/follow-up`

### The Prompt:
```python
prompt = f"""🚨🚨🚨 RULE #1: PERSON NAMES 🚨🚨🚨
BEFORE DOING ANYTHING ELSE, CHECK IF THE QUERY MENTIONS A PERSON'S NAME.

USER QUERY: "{user_query}"

Does this query mention a person's name (like "Chris Johnson", "Dr. Smith", "Judge Lee", etc.)?
- CRITICAL: Three types of person searches:
  1. WHO SENT the message (listserv poster) → posted_by
  2. MEDICAL/LEGAL EXPERT discussed (QME, doctor, witness) → author_first_name/author_last_name
  3. GENERAL mentions or case names → keywords_any

- EXAMPLES: 
  ✓ "messages BY Ramin Saedi" → posted_by: "Ramin Saedi" (full name - who sent to listserv)
  ✓ "written by Chris Johnson" → posted_by: "Chris Johnson" (full name - who sent to listserv)
  ✓ "articles by Johnson" → author_last_name: "Johnson" (last name only given)
  ✓ "QME Dr. John Smith" → author_first_name: "John", author_last_name: "Smith" (medical expert - BOTH names)
  ✓ "expert Dr. Sarah Lee" → author_first_name: "Sarah", author_last_name: "Lee" (medical expert - BOTH names)
  ✓ "expert testimony from Dr. Johnson" → author_last_name: "Johnson" (medical expert - only last name given)
  ✓ "discussions about Paterson case" → keywords_any: "Paterson" (case name, NOT a person)

TODAY'S DATE: {today.strftime('%Y-%m-%d')}

Your task: Analyze this query and determine the BEST search parameters to find relevant messages.

Available search fields:
1. posted_by - 🚨 Filter by WHO SENT the message (e.g., "messages BY Ray Saedi" → "Ray Saedi")
2. author_first_name + author_last_name - 🏥 For WITNESS/EXPERT searches (QMEs, doctors, medical experts)
3. keyword - Simple keyword search (searches subject + body)
4. keywords_all - Must contain ALL these keywords (comma-separated: "word1, word2, word3")
5. keywords_phrase - Exact phrase match (e.g., "permanent disability rating")
6. keywords_any - Must contain at least ONE of these (comma-separated: "term1, term2, term3")
7. keywords_exclude - Must NOT contain these keywords (comma-separated)
8. listserv - Which list: "all", "lawnet", "lavaaa", "lamaaa", "scaaa"
9. attachment_filter - "all", "with_attachments", "without_attachments"
10. date_from - Start date (YYYY-MM-DD)
11. date_to - End date (YYYY-MM-DD)
12. search_in - "subject_and_body" or "subject_only"

SEARCH STRATEGY:
1. keywords_any = BROAD search → Use for comprehensive results
2. keywords_all = NARROW search → Use when multiple concepts MUST co-occur
3. Temporal keywords → USE DATE FILTERS ("recent" = 6 months ago)
4. Person names → Use correct field (posted_by vs author_first_name/author_last_name)

Respond in JSON format:
{
  "reasoning": "Brief explanation of search strategy",
  "parameters": {
    "keyword": "string or null",
    "keywords_all": "comma-separated terms or null",
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
  }
}"""
```

### Response Format:
```json
{
  "reasoning": "User wants recent QME panel procedures. Using keywords_any for broad search and date filter for 'recent'.",
  "parameters": {
    "keywords_any": "QME, panel, procedures",
    "date_from": "2024-06-05",
    "date_to": null
  }
}
```

### Code Flow - Path A (Direct):
```python
# app.py line 368-373 (if query is specific)
enhancer = QueryEnhancer()
search_params = enhancer.enhance_query(request.intent)  # ← Direct call

# query_enhancer.py line 58-66
response = self.client.messages.create(
    model=self.model,
    max_tokens=800,
    system="You are an expert at California workers' compensation law... Always respond with valid JSON.",
    messages=[{"role": "user", "content": prompt}]
)

# Parse and convert to SearchParams
params = data.get('parameters', {})
search_params = SearchParams(...)
```

### Code Flow - Path B (After Follow-up):
```python
# app.py line 420-445 (/api/ai/follow-up endpoint)
# User answered follow-up question

# Combine original query + user's answer
original_query = "QME panel procedures"  # From conversation history
user_answer = "psychiatric evaluations and panel selection"
refined_query = f"{original_query}. Specifically: {user_answer}"
# Result: "QME panel procedures. Specifically: psychiatric evaluations and panel selection"

# Pass refined query to QueryEnhancer
enhancer = QueryEnhancer()
search_params = enhancer.enhance_query(refined_query)  # ← Uses refined query

# QueryEnhancer processes the refined query with same prompt
# Now has more context: "psychiatric evaluations and panel selection"
```

### ⚠️ **IMPORTANT:** QueryEnhancer Does NOT Ask Follow-ups
- QueryEnhancer always returns search parameters
- It never asks for clarification
- If it needs more info, it makes best-guess parameters
- Only the Vagueness Check (PROMPT 1) asks follow-ups

---

## **PROMPT 3: Message Relevance Analysis** (`ai_analyzer.py` lines 108-171)

**Location:** `AIAnalyzer.analyze_relevance()`  
**Purpose:** Score each scraped message for relevance to user's query  
**Model:** Claude 4.5 Opus  
**Temperature:** Not specified (defaults to ~0.7)  
**Max Tokens:** 500

### When This Prompt Runs:
- After scraper finds messages
- For EACH message found
- Uses the ORIGINAL user query (not refined query)

### The Prompt:
```python
prompt = f"""You are an expert California workers' compensation attorney analyzing a listserv message from CAAA (California Applicants' Attorneys Association) to determine if it provides substantive information that helps answer a specific legal question.

CONTEXT:
This message is from a professional legal discussion forum where experienced workers' compensation attorneys discuss case strategies, statutory interpretations, procedural questions, and share practical insights from their practice.

USER'S LEGAL QUESTION:
"{search_keyword}"
{additional_context if provided}

LISTSERV MESSAGE:
From: {from_name}
Subject: {subject}

{body}

🚨 CRITICAL RULE - AUTHOR-FOCUSED SEARCHES 🚨
IF the user's question is ONLY asking for messages FROM or MENTIONING a specific person (examples: "messages from Ray Saedi", "posts by John Smith", "find ALL messages from author: Johnson"), then:
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
{
  "is_relevant": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Explain specifically what legal information this message provides (or fails to provide) in relation to the user's question"
}"""
```

### Response Format:
```json
{
  "is_relevant": true,
  "confidence": 0.85,
  "reasoning": "Message discusses QME panel selection procedures for psychiatric evaluations, directly addressing the user's question."
}
```

### Code Flow:
```python
# ai_analyzer.py line 60-65
response = self.client.messages.create(
    model=self.model,
    max_tokens=500,
    system="You are an expert legal assistant. Always respond with valid JSON.",
    messages=[{"role": "user", "content": prompt}]
)

# Parse response (line 174-191)
raw = response.content[0].text
match = re.search(r"\{[\s\S]*\}", raw)
content = match.group() if match else raw
data = json.loads(content)

return {
    'is_relevant': bool(data.get('is_relevant', False)),
    'confidence': float(data.get('confidence', 0.0)),
    'reasoning': str(data.get('reasoning', 'No reasoning provided'))
}
```

---

## 🔄 **Complete Flow Diagram with Follow-ups**

```
USER QUERY: "QME panel procedures"
    │
    ▼
┌─────────────────────────────────────┐
│  PROMPT 1: Vagueness Check          │
│  (app.py /api/ai/analyze)           │
│  ─────────────────────────────────  │
│  Input: "QME panel procedures"     │
│  Output: {                           │
│    "is_vague": true,                 │
│    "follow_up_question": "What..."  │
│  }                                   │
└─────────────────────────────────────┘
    │
    │ (is_vague = true)
    ▼
┌─────────────────────────────────────┐
│  FRONTEND: Show Follow-up Question  │
│  "What specific aspect of QME..."   │
└─────────────────────────────────────┘
    │
    │ (user answers)
    ▼
USER ANSWER: "psychiatric evaluations and panel selection"
    │
    ▼
┌─────────────────────────────────────┐
│  /api/ai/follow-up endpoint         │
│  (app.py line 420)                  │
│  ─────────────────────────────────  │
│  Combines:                           │
│  original_query + user_answer        │
│  → "QME panel procedures.          │
│     Specifically: psychiatric..."   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  PROMPT 2: Query Enhancement        │
│  (query_enhancer.py)                 │
│  ─────────────────────────────────   │
│  Input: Refined query with context   │
│  Output: {                           │
│    "parameters": {                   │
│      "keywords_any": "QME, panel...",│
│      "date_from": "2024-06-05"       │
│    }                                 │
│  }                                   │
└─────────────────────────────────────┘
    │
    │ (converts to SearchParams)
    ▼
┌─────────────────────────────────────┐
│  SCRAPER: Run Search                │
│  (scraper.py)                       │
│  ─────────────────────────────────   │
│  Finds: 15 messages                 │
└─────────────────────────────────────┘
    │
    │ (for each message)
    ▼
┌─────────────────────────────────────┐
│  PROMPT 3: Relevance Analysis      │
│  (ai_analyzer.py)                   │
│  ─────────────────────────────────   │
│  Input: Message + Original Query    │
│  (Uses original: "QME panel...")   │
│  Output: {                           │
│    "is_relevant": true,              │
│    "confidence": 0.85,               │
│    "reasoning": "Message discusses..."│
│  }                                   │
└─────────────────────────────────────┘
    │
    │ (filter by is_relevant=true)
    ▼
┌─────────────────────────────────────┐
│  RESULTS: Show to User              │
│  (frontend)                         │
└─────────────────────────────────────┘
```

---

## 📊 **Key Issues Identified**

### Issue 1: Vagueness Check Too Aggressive
**Problem:** Prompt 1 asks follow-ups for queries that are actually clear:
- ❌ "messages from Ramin Saedi" → Asks "What type of messages?"
- ❌ "QME panel procedures" → Asks "Which aspect?"

**Why:** The prompt doesn't trust Claude's knowledge of:
- Common legal acronyms (QME = Qualified Medical Examiner)
- Clear intent phrases ("from X" = sender filter)
- Standard legal terms

**Impact:** User frustration - unnecessary follow-ups

### Issue 2: QueryEnhancer Never Asks Follow-ups
**Problem:** QueryEnhancer always returns parameters, even if query is ambiguous

**Current Behavior:**
- QueryEnhancer receives: "QME panel procedures"
- Makes best guess: `keywords_any: "QME, panel, procedures"`
- Never asks: "Do you want psychiatric, orthopedic, or general QME panels?"

**Impact:** Less precise search parameters

### Issue 3: No Temperature Control
**Problem:** All prompts use default temperature (~0.7), which may be too creative

**Impact:** 
- Inconsistent JSON formatting
- Overly creative interpretations
- Less deterministic results

### Issue 4: Follow-up Questions Too Generic
**Problem:** When vagueness check does ask follow-ups, they're not helpful:
- "What type of messages?" (obvious - listserv messages!)
- "Which aspect?" (should infer from context)

**Why:** The prompt doesn't leverage Claude's domain knowledge to infer intent

---

## 🎯 **Recommendations for Improvement**

### 1. **Trust Claude's Knowledge More (Vagueness Check)**
- Remove unnecessary follow-ups for clear queries
- Let Claude infer intent from context
- Only ask follow-ups for genuinely ambiguous queries
- Add examples of queries that DON'T need follow-ups

### 2. **Allow QueryEnhancer to Ask Follow-ups**
- Add optional follow-up capability to QueryEnhancer
- Ask when query is ambiguous but not vague enough for Prompt 1
- Example: "QME panel" → "Which medical specialty?"

### 3. **Add Temperature Control**
- Vagueness check: `temperature=0.1` (more deterministic)
- Query enhancement: `temperature=0.2` (slight creativity for synonyms)
- Relevance analysis: `temperature=0.1` (consistent scoring)

### 4. **Improve Follow-up Questions**
- Use Claude's legal domain knowledge
- Ask specific, actionable questions
- Provide examples in the prompt of good follow-up questions

### 5. **Better Prompt Structure**
- Use XML tags for better structure
- Add examples of good vs bad responses
- Specify output format more explicitly

