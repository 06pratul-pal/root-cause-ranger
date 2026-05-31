# 🏴‍☠️ Root Cause Ranger

AI Agent that automatically investigates production incidents using Coral SQL.

Built for Pirates of the Coral-bean Hackathon — Track 1 Enterprise.

## The Problem

When production crashes, engineers manually check 4 tools:
- GitHub — what code changed? (10 min)
- Sentry — what error came? (10 min)  
- Slack — what did team say? (10 min)
- Datadog — which metric failed? (10 min)

Total = 40 minutes of manual work every incident.

## The Solution

One command. 30 seconds. Root cause found.

Agent automatically:
1. Queries GitHub via Coral SQL
2. Reads actual source code files
3. Finds exact bug — file + line number
4. Finds which PR introduced the bug
5. Writes full incident report

## Demo

Run the website, click Pay Now 3 times, watch agent auto-investigate!

## Coral SQL

```sql
SELECT number, title, body
FROM github.issues
WHERE owner = 'mycompany'
AND repo = 'payment-service'
ORDER BY created_at DESC LIMIT 10;
```

Zero ETL. Zero API code. Just SQL.

## Setup

Install Coral, connect GitHub, add API keys, run agent.

## Tech Stack

- Coral SQL — GitHub data queries
- OpenAI GPT-4o — AI reasoning
- Flask — Demo website
- GitHub — Real code analysis
