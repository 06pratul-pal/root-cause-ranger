from openai import OpenAI
import subprocess
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CORAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "coral_sql",
            "description": "Run SQL query against Coral/GitHub. Use for querying files, commits, PRs, issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query to run"}
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Get the actual content of a file from GitHub repository. Use this to find exact bug location, line numbers, and what changed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "File path to fetch e.g. payment.py, database.py, config.py"
                    }
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_commits",
            "description": "Get recent commits to find what changed recently in the codebase.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pull_requests",
            "description": "Get recent pull requests to find which PR introduced the bug.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_issues",
            "description": "Get open GitHub issues to understand what errors users are reporting.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = "06pratul-pal"
GITHUB_REPO = "payment-service"

def run_coral_sql(sql: str) -> dict:
    try:
        result = subprocess.run(
            ["coral", "sql", "--format", "json", sql],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0 and result.stderr:
            return {"error": result.stderr.strip(), "rows": []}
        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                if isinstance(data, list):
                    return {"rows": data, "count": len(data)}
                return {"rows": [data], "count": 1}
            except:
                return {"rows": [], "raw": result.stdout.strip()}
        return {"rows": [], "count": 0}
    except Exception as e:
        return {"error": str(e)}

def get_file_content(filepath: str) -> dict:
    """Fetch actual file content from GitHub"""
    try:
        import requests
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{filepath}"
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            
            # Add line numbers
            lines = content.split("\n")
            numbered = []
            for i, line in enumerate(lines, 1):
                numbered.append(f"Line {i:3d}: {line}")
            
            return {
                "file": filepath,
                "content": "\n".join(numbered),
                "total_lines": len(lines),
                "last_modified": data.get("sha", "unknown")
            }
        else:
            return {"error": f"File not found: {filepath} ({response.status_code})"}
    except Exception as e:
        return {"error": str(e)}

def get_recent_commits() -> dict:
    try:
        import requests
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits"
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        response = requests.get(url, headers=headers, params={"per_page": 10})
        if response.status_code == 200:
            commits = response.json()
            result = []
            for c in commits:
                result.append({
                    "sha": c["sha"][:7],
                    "message": c["commit"]["message"],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"],
                    "url": c["html_url"]
                })
            return {"commits": result, "count": len(result)}
        return {"error": f"GitHub API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_pull_requests() -> dict:
    try:
        import requests
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls"
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        response = requests.get(url, headers=headers, 
                              params={"state": "all", "per_page": 10})
        if response.status_code == 200:
            prs = response.json()
            result = []
            for pr in prs:
                result.append({
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "author": pr["user"]["login"],
                    "created_at": pr["created_at"],
                    "body": pr["body"]
                })
            return {"pull_requests": result, "count": len(result)}
        return {"error": f"GitHub API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_issues() -> dict:
    try:
        import requests
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        response = requests.get(url, headers=headers,
                              params={"state": "open", "per_page": 10})
        if response.status_code == 200:
            issues = response.json()
            result = []
            for issue in issues:
                if "pull_request" not in issue:
                    result.append({
                        "number": issue["number"],
                        "title": issue["title"],
                        "body": issue["body"],
                        "created_at": issue["created_at"]
                    })
            return {"issues": result, "count": len(result)}
        return {"error": f"GitHub API error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def handle_tool_call(tool_name: str, tool_args: dict) -> str:
    if tool_name == "coral_sql":
        sql = tool_args.get("sql", "")
        preview = sql.strip().replace("\n", " ")[:80]
        print(f"\n  🔧 Coral SQL: {preview}...")
        result = run_coral_sql(sql)
        rows = result.get("rows", [])
        print(f"  ✅ Returned {len(rows)} rows")
        return json.dumps(result, indent=2, default=str)

    elif tool_name == "get_file_content":
        filepath = tool_args.get("filepath", "")
        print(f"\n  📄 Reading file: {filepath}")
        result = get_file_content(filepath)
        if "error" not in result:
            print(f"  ✅ Got {result.get('total_lines', 0)} lines")
        else:
            print(f"  ❌ {result['error']}")
        return json.dumps(result, indent=2, default=str)

    elif tool_name == "get_recent_commits":
        print(f"\n  📝 Fetching recent commits...")
        result = get_recent_commits()
        print(f"  ✅ Got {result.get('count', 0)} commits")
        return json.dumps(result, indent=2, default=str)

    elif tool_name == "get_pull_requests":
        print(f"\n  🔀 Fetching pull requests...")
        result = get_pull_requests()
        print(f"  ✅ Got {result.get('count', 0)} PRs")
        return json.dumps(result, indent=2, default=str)

    elif tool_name == "get_issues":
        print(f"\n  🚨 Fetching open issues...")
        result = get_issues()
        print(f"  ✅ Got {result.get('count', 0)} issues")
        return json.dumps(result, indent=2, default=str)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})

def run_agent(repo_owner="06pratul-pal", repo_name="payment-service", alert_message=""):
    print("\n" + "="*60)
    print("  🏴‍☠️  ROOT CAUSE RANGER — Coral Agent")
    print("="*60)
    print(f"  🎯 Repo   : {repo_owner}/{repo_name}")
    print(f"  🕐 Time   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🚨 Alert  : {alert_message or 'Production alert fired!'}")
    print("="*60)

    system_prompt = f"""You are Root Cause Ranger — an expert SRE AI agent.

ALERT: Production is down! You must find the EXACT bug.

You have these tools:
1. coral_sql — query GitHub data using SQL
2. get_file_content — READ ACTUAL FILE CONTENT with line numbers
3. get_recent_commits — see what changed recently
4. get_pull_requests — find which PR caused the bug
5. get_issues — see what errors users reported

YOUR EXACT INVESTIGATION STEPS:
1. get_issues — what are users reporting?
2. get_pull_requests — which PR merged recently?
3. get_recent_commits — what files changed?
4. get_file_content("payment.py") — read the actual file!
5. get_file_content("database.py") — read this file too!
6. get_file_content("config.py") — check config!
7. Find the EXACT line number where bug is
8. Write report

IMPORTANT: You MUST read the actual files to find:
- Which FILE has the bug
- Which LINE number
- What the bug is exactly
- Which PR introduced it

After investigation write this report:

========================================
🚨 ROOT CAUSE RANGER — INCIDENT REPORT
========================================

📁 BUG LOCATION:
File: [exact filename]
Line: [exact line number]
Code: [the buggy line of code]

🔀 INTRODUCED BY:
PR: [PR number and title]
Author: [who made this change]
Date: [when]

🚨 WHAT BROKE:
[One sentence]

⏰ TIMELINE:
[Events with times]

🔍 ROOT CAUSE:
[Exact technical explanation]

📊 IMPACT:
[Users affected, errors]

✅ EXACT FIX:
File: [filename]
Line: [line number]
Change: [exact code change needed]

🛡️ PREVENTION:
[How to prevent]
========================================"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""🚨 PRODUCTION ALERT!
            
Alert: {alert_message or 'Payment service is down!'}
Repo: {repo_owner}/{repo_name}

Users cannot checkout. Find the EXACT bug — which file, which line, which PR caused this!
Read the actual source code files to find the root cause!"""
        }
    ]

    step = 0
    max_steps = 15

    while step < max_steps:
        step += 1
        print(f"\n  🤔 Step {step}...")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=CORAL_TOOLS,
            tool_choice="auto"
        )

        message = response.choices[0].message
        messages.append(message)

        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                result = handle_tool_call(tool_name, tool_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        else:
            final_text = message.content
            print(f"\n{'='*60}")
            print("  📋 FINAL REPORT")
            print("="*60)
            print(final_text)

            report_path = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# 🏴‍☠️ Root Cause Ranger\n\n")
                f.write(f"**Repo:** {repo_owner}/{repo_name}\n")
                f.write(f"**Time:** {datetime.now().isoformat()}\n\n")
                f.write(final_text)

            print(f"\n  💾 Report: {report_path}")
            print(f"  ✅ Done in {step} steps!")
            return final_text

    return "Investigation complete."

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and "/" in sys.argv[1]:
        owner, repo = sys.argv[1].split("/", 1)
    else:
        owner, repo = "06pratul-pal", "payment-service"
    run_agent(repo_owner=owner, repo_name=repo)