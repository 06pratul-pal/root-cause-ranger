from flask import Flask, jsonify, render_template_string
import requests
import os
import subprocess
import threading
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Intentional bug - pool size too small
DB_POOL_SIZE = 5  # BUG: should be 20
DB_CONNECTIONS_USED = 0

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = "06pratul-pal"
GITHUB_REPO = "payment-service"

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>PayFast — Payment Service</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: Arial, sans-serif; 
            background: #0a0a0a; 
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background: #1a1a2e;
            border-radius: 16px;
            padding: 40px;
            width: 420px;
            border: 1px solid #333;
        }
        h1 { 
            color: #00d4ff; 
            margin-bottom: 8px;
            font-size: 28px;
        }
        .subtitle { color: #666; margin-bottom: 30px; font-size: 14px; }
        .order-box {
            background: #0f0f23;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            border: 1px solid #222;
        }
        .order-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #222;
            font-size: 14px;
            color: #ccc;
        }
        .order-item:last-child { border-bottom: none; }
        .total {
            display: flex;
            justify-content: space-between;
            padding: 12px 0 0;
            font-weight: bold;
            font-size: 18px;
            color: white;
        }
        .status-bar {
            background: #0f0f23;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 20px;
            font-size: 13px;
            font-family: monospace;
        }
        .status-ok { color: #00ff88; }
        .status-warn { color: #ffaa00; }
        .status-error { color: #ff4444; }
        button {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #00d4ff, #0088cc);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
        }
        button:hover { transform: translateY(-2px); opacity: 0.9; }
        button:disabled { background: #333; cursor: not-allowed; transform: none; }
        .result {
            margin-top: 20px;
            padding: 16px;
            border-radius: 10px;
            font-size: 14px;
            display: none;
        }
        .result.success { background: rgba(0,255,136,0.1); border: 1px solid #00ff88; color: #00ff88; }
        .result.error { background: rgba(255,68,68,0.1); border: 1px solid #ff4444; color: #ff4444; }
        .agent-box {
            margin-top: 16px;
            padding: 16px;
            border-radius: 10px;
            background: rgba(0,212,255,0.05);
            border: 1px solid #00d4ff33;
            font-size: 13px;
            color: #00d4ff;
            display: none;
            font-family: monospace;
        }
        .pool-bar {
            height: 8px;
            background: #222;
            border-radius: 4px;
            margin-top: 8px;
            overflow: hidden;
        }
        .pool-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff88, #ffaa00, #ff4444);
            border-radius: 4px;
            transition: width 0.5s;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ PayFast</h1>
        <p class="subtitle">Production Payment Service</p>
        
        <div class="status-bar">
            <div>DB Pool: <span id="pool-status" class="status-ok">Ready</span></div>
            <div class="pool-bar">
                <div class="pool-fill" id="pool-bar" style="width: 0%"></div>
            </div>
        </div>

        <div class="order-box">
            <div class="order-item"><span>iPhone 15 Pro</span><span>₹1,29,999</span></div>
            <div class="order-item"><span>AirPods Pro</span><span>₹24,999</span></div>
            <div class="order-item"><span>Shipping</span><span>FREE</span></div>
            <div class="total"><span>Total</span><span>₹1,54,998</span></div>
        </div>

        <button onclick="checkout()" id="btn">💳 Pay Now</button>
        
        <div class="result" id="result"></div>
        <div class="agent-box" id="agent-box"></div>
    </div>

    <script>
        let clickCount = 0;

        async function checkout() {
            clickCount++;
            const btn = document.getElementById('btn');
            const result = document.getElementById('result');
            const agentBox = document.getElementById('agent-box');
            const poolStatus = document.getElementById('pool-status');
            const poolBar = document.getElementById('pool-bar');
            
            btn.disabled = true;
            btn.textContent = '⏳ Processing...';
            result.style.display = 'none';
            agentBox.style.display = 'none';

            // Update pool bar
            const poolPercent = Math.min(clickCount * 20, 100);
            poolBar.style.width = poolPercent + '%';
            
            if (poolPercent >= 80) {
                poolStatus.textContent = 'CRITICAL';
                poolStatus.className = 'status-error';
            } else if (poolPercent >= 40) {
                poolStatus.textContent = 'WARNING';  
                poolStatus.className = 'status-warn';
            }

            try {
                const response = await fetch('/checkout', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({amount: 154998, user: 'user_' + clickCount})
                });
                const data = await response.json();

                result.style.display = 'block';
                
                if (data.status === 'success') {
                    result.className = 'result success';
                    result.innerHTML = '✅ Payment successful! Order #' + data.order_id;
                    poolStatus.textContent = 'OK';
                    poolStatus.className = 'status-ok';
                } else {
                    result.className = 'result error';
                    result.innerHTML = '❌ ' + data.error + '<br><small>' + data.detail + '</small>';
                    
                    // Show agent investigating
                    
                }
            } catch(e) {
                result.style.display = 'block';
                result.className = 'result error';
                result.innerHTML = '❌ Server error: ' + e.message;
            }

            btn.disabled = false;
            btn.textContent = '💳 Pay Now';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/checkout', methods=['POST'])
def checkout():
    global DB_CONNECTIONS_USED
    DB_CONNECTIONS_USED += 1
    
    # Simulate bug — pool exhausts after 3 requests
    if DB_CONNECTIONS_USED > DB_POOL_SIZE - 3:
        
        # Auto create GitHub issue
        create_github_issue(DB_CONNECTIONS_USED)
        
        # Auto run agent in background
        threading.Thread(target=run_agent_background).start()
        
        return jsonify({
            "status": "error",
            "error": "DatabaseConnectionTimeout",
            "detail": f"DB pool exhausted! ({DB_CONNECTIONS_USED}/{DB_POOL_SIZE} connections used). Payment failed.",
            "users_affected": DB_CONNECTIONS_USED * 50
        }), 500
    
    return jsonify({
        "status": "success",
        "order_id": f"ORD{DB_CONNECTIONS_USED:04d}",
        "message": "Payment processed successfully"
    })

def create_github_issue(connection_count):
    if not GITHUB_TOKEN:
        print("No GitHub token — skipping issue creation")
        return
    
    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "title": f"🚨 ALERT: Payment service down — DB pool exhausted",
            "body": f"""## Production Incident Alert

**Time:** Auto-detected
**Severity:** CRITICAL

### What happened:
DB connection pool exhausted ({connection_count}/{DB_POOL_SIZE} connections used)
Payment transactions failing with DatabaseConnectionTimeout

### Error:

### Impact:
- Users cannot checkout
- Estimated affected users: {connection_count * 50}

### Triggered by:
Root Cause Ranger — automatic alert detection
"""
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            print(f"✅ GitHub Issue created automatically!")
        else:
            print(f"GitHub issue failed: {response.status_code}")
    except Exception as e:
        print(f"GitHub issue error: {e}")

def run_agent_background():
    try:
        print("\n🏴‍☠️ Alert fired! Running Root Cause Ranger automatically...")
        subprocess.run([
            r"venv\Scripts\python.exe", "agent.py",
            "--repo", f"{GITHUB_OWNER}/{GITHUB_REPO}"
        ], cwd=os.getcwd())
    except Exception as e:
        print(f"Agent error: {e}")

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  ⚡ PayFast — Payment Service")
    print("="*50)
    print("  Open browser: http://localhost:5000")
    print("  Click 'Pay Now' 3-4 times to trigger bug!")
    print("  Watch agent auto-run in terminal!")
    print("="*50 + "\n")
    app.run(debug=False, port=5000)