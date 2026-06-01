# 🏴‍☠️ Root Cause Ranger

AI Agent that automatically investigates production incidents using Coral SQL.
Built for Pirates of the Coral-bean Hackathon — Track 1 (Enterprise)

## The Problem
When production crashes, engineers manually check 4 different tools — GitHub, Sentry, Slack, Datadog. This takes 40 minutes. Every minute = money lost.

## The Solution
Root Cause Ranger automatically:
1. Detects the crash
2. Creates GitHub issue automatically
3. Reads actual source code files
4. Finds exact bug — file name + line number
5. Tells which PR introduced it
6. All in 25 seconds!

## Demo Output
BUG LOCATION:
File: config.py
Line: 8
Code: DB_POOL_SIZE = 5 (should be 20)

INTRODUCED BY: PR #2
Author: 06pratul-pal
FIX: Change DB_POOL_SIZE = 5 to DB_POOL_SIZE = 20

## How to Run

Step 1 - Install Coral
irm https://withcoral.com/install.ps1 | iex

Step 2 - Connect GitHub
coral source add --interactive github

Step 3 - Setup
pip install -r requirements.txt
cp .env.example .env

Step 4 - Run Demo Website
python app.py
Open http://localhost:5000
Click Pay Now 3 times to trigger bug!

Step 5 - Run Agent
python agent.py --repo owner/repo

## Tech Stack
- Coral SQL — queries GitHub data
- OpenAI GPT-4o — AI reasoning
- Flask — demo website
- GitHub API — source code analysis

## How Coral SQL is Used
SELECT number, title, body FROM github.issues
WHERE owner = 'mycompany'
AND repo = 'payment-service'
LIMIT 10

Zero ETL. Zero glue code. 100% local.

## Project Structure
agent.py — Main AI agent
app.py — Demo payment website
requirements.txt — Dependencies
.env.example — API keys template
