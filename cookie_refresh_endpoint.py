"""
Add this to app.py to create a cookie refresh endpoint
"""

# Add to app.py:

@app.get("/admin/refresh-cookies")
async def refresh_cookies_page():
    """Web page for refreshing CAAA login cookies"""
    
    # Stop persistent browser and launch cookie capture
    import subprocess
    subprocess.run(["systemctl", "stop", "caaa-browser"])
    
    # Launch cookie capture in background
    subprocess.Popen([
        "/srv/caaa_scraper/venv/bin/python",
        "/srv/caaa_scraper/cookie_capture.py"
    ], env={"DISPLAY": ":99"})
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Refresh CAAA Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #333; }
            .step {
                background: #e3f2fd;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #2196f3;
            }
            .btn {
                display: inline-block;
                padding: 15px 30px;
                background: #2196f3;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-size: 18px;
                margin: 20px 0;
            }
            .btn:hover { background: #1976d2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Refresh CAAA Login Cookies</h1>
            
            <div class="step">
                <strong>Step 1:</strong> Click the button below to open the login window
            </div>
            
            <a href="http://134.199.196.31:6080/vnc.html" target="_blank" class="btn">
                🖥️ Open Login Window
            </a>
            
            <div class="step">
                <strong>Step 2:</strong> In the new window, log into CAAA with your credentials
            </div>
            
            <div class="step">
                <strong>Step 3:</strong> After logging in successfully, close this tab. The system will automatically save your login and restart.
            </div>
            
            <p style="color: #666; margin-top: 30px;">
                <strong>Note:</strong> The login window opens in a remote desktop viewer. 
                Everything happens on the server - nothing is installed on your computer.
            </p>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

