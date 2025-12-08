#!/usr/bin/env python3
"""Update all AI modules to use Claude 4.5 Opus"""
import re

MODEL = "claude-sonnet-4-20250514"

def update_query_enhancer():
    with open("/srv/caaa_scraper/query_enhancer.py", "r") as f:
        content = f.read()
    
    # 1. Replace import
    content = content.replace("from openai import OpenAI", "import anthropic\nimport re as regex")
    
    # 2. Replace init
    content = re.sub(
        r'ollama_url = os\.getenv.*?self\.model = "qwen2\.5:32b"',
        f'''api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "{MODEL}"''',
        content,
        flags=re.DOTALL
    )
    
    # 3. Replace API call
    content = re.sub(
        r'response = self\.client\.chat\.completions\.create\(\s*model=self\.model,\s*messages=\[\s*\{\s*"role": "system",\s*"content": "([^"]+)"\s*\},\s*\{\s*"role": "user",\s*"content": prompt\s*\}\s*\],\s*response_format=\{"type": "json_object"\},\s*temperature=([0-9.]+),\s*max_tokens=(\d+)\s*\)',
        r'''response = self.client.messages.create(
                model=self.model,
                max_tokens=\3,
                system="\1 Always respond with valid JSON.",
                messages=[{"role": "user", "content": prompt}]
            )''',
        content
    )
    
    # 4. Replace response parsing
    content = content.replace(
        "content = response.choices[0].message.content",
        '''raw = response.content[0].text
            # Extract JSON from response
            match = regex.search(r"\\{[\\s\\S]*\\}", raw)
            content = match.group() if match else raw'''
    )
    
    with open("/srv/caaa_scraper/query_enhancer.py", "w") as f:
        f.write(content)
    print("✓ query_enhancer.py updated")

def update_ai_analyzer():
    with open("/srv/caaa_scraper/ai_analyzer.py", "r") as f:
        content = f.read()
    
    # 1. Replace import
    content = content.replace("from openai import OpenAI", "import anthropic\nimport re as regex")
    
    # 2. Replace init  
    content = re.sub(
        r'ollama_url = os\.getenv.*?self\.model = "qwen2\.5:32b"',
        f'''api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "{MODEL}"''',
        content,
        flags=re.DOTALL
    )
    
    # 3. Replace API call
    content = re.sub(
        r'response = self\.client\.chat\.completions\.create\(\s*model=self\.model,\s*messages=\[\s*\{"role": "system", "content": system_prompt\},\s*\{"role": "user", "content": user_prompt\}\s*\],\s*response_format=\{"type": "json_object"\},\s*temperature=([0-9.]+),\s*max_tokens=(\d+)\s*\)',
        r'''response = self.client.messages.create(
                model=self.model,
                max_tokens=\2,
                system=system_prompt + " Always respond with valid JSON.",
                messages=[{"role": "user", "content": user_prompt}]
            )''',
        content
    )
    
    # 4. Replace response parsing
    content = content.replace(
        "result = json.loads(response.choices[0].message.content)",
        '''raw = response.content[0].text
            match = regex.search(r"\\{[\\s\\S]*\\}", raw)
            result = json.loads(match.group() if match else raw)'''
    )
    
    with open("/srv/caaa_scraper/ai_analyzer.py", "w") as f:
        f.write(content)
    print("✓ ai_analyzer.py updated")

def update_orchestrator():
    with open("/srv/caaa_scraper/orchestrator.py", "r") as f:
        content = f.read()
    
    # 1. Replace import
    content = content.replace("from openai import OpenAI", "import anthropic")
    
    # 2. Replace client init
    content = re.sub(
        r'ollama_url = os\.getenv.*?api_key="ollama".*?\)',
        '''api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None''',
        content,
        flags=re.DOTALL
    )
    
    # 3. Update print message
    content = content.replace("Qwen 14B on Vast.ai GPU via tunnel", "Claude 4.5 Opus")
    content = content.replace("Qwen 32B", "Claude 4.5")
    
    with open("/srv/caaa_scraper/orchestrator.py", "w") as f:
        f.write(content)
    print("✓ orchestrator.py updated")

def update_app():
    with open("/srv/caaa_scraper/app.py", "r") as f:
        content = f.read()
    
    # 1. Replace model name
    content = content.replace('model="qwen2.5:32b"', f'model="{MODEL}"')
    
    # 2. Replace API call style (vagueness check) - be more flexible with the pattern
    old_call = '''orchestrator.client.chat.completions.create(
            model="''' + MODEL + '''",
            messages=[{"role": "user", "content": vagueness_check}],
            response_format={"type": "json_object"},
            temperature=0.3
        )'''
    
    new_call = f'''orchestrator.client.messages.create(
            model="{MODEL}",
            max_tokens=500,
            messages=[{{"role": "user", "content": vagueness_check + " Respond with JSON only."}}]
        )'''
    
    content = content.replace(old_call, new_call)
    
    # Also try the original pattern
    content = re.sub(
        r'orchestrator\.client\.chat\.completions\.create\(\s*model="[^"]+",\s*messages=\[\{"role": "user", "content": vagueness_check\}\],\s*response_format=\{"type": "json_object"\},\s*temperature=[0-9.]+\s*\)',
        f'''orchestrator.client.messages.create(
            model="{MODEL}",
            max_tokens=500,
            messages=[{{"role": "user", "content": vagueness_check + " Respond with JSON only."}}]
        )''',
        content
    )
    
    # 3. Replace response parsing
    content = content.replace(
        "vagueness_result = json.loads(vagueness_response.choices[0].message.content)",
        '''_raw = vagueness_response.content[0].text
        import re as _re
        _match = _re.search(r"\\{[\\s\\S]*\\}", _raw)
        vagueness_result = json.loads(_match.group() if _match else _raw)'''
    )
    
    with open("/srv/caaa_scraper/app.py", "w") as f:
        f.write(content)
    print("✓ app.py updated")

if __name__ == "__main__":
    update_query_enhancer()
    update_ai_analyzer()
    update_orchestrator()
    update_app()
    print("\n✓ All files updated to use Claude 4.5 Opus")

