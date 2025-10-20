# Cookie Capture Checklist - CAAA Login

## Pre-Call Preparation (Dev)

### 1. VM Setup
- [ ] VM provisioned and accessible via SSH
- [ ] Ubuntu/Debian with 2 vCPU, 2-4 GB RAM
- [ ] Python 3.10+ installed
- [ ] Install dependencies:
  ```bash
  sudo apt update
  sudo apt install -y python3-pip python3-venv
  ```

### 2. Install Playwright & Dependencies
```bash
# Create project directory
mkdir -p /srv/caaa_scraper
cd /srv/caaa_scraper

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install playwright cryptography

# Install browser binaries
playwright install chromium
playwright install-deps  # System dependencies
```

### 3. Residential Proxy (if ready)
- [ ] Proxy credentials obtained
- [ ] Test proxy connectivity:
  ```bash
  curl -x http://username:password@proxy-host:port https://ipinfo.io
  ```
- [ ] Note the proxy IP for fingerprint consistency

### 4. Upload Cookie Capture Script
```bash
# From your local machine
scp cookie_capture.py ubuntu@<vm-ip>:/srv/caaa_scraper/
```

### 5. Create .gitignore
```bash
cat > /srv/caaa_scraper/.gitignore << 'EOF'
auth.json
auth.json.enc
.auth_key
venv/
__pycache__/
*.pyc
.env
EOF
```

---

## During Call with Client

### Phase 1: Briefing (2 min)
Say to client:
> "We're going to capture your login session securely. You'll type your password yourself on our secure server—I'll never see or store your actual password. The whole process takes about 5 minutes. Ready?"

Ask client:
- [ ] "Does your login require a code via text/email/app after entering your password?"
- [ ] "Have you seen image challenges (CAPTCHA) when logging in from new places?"
- [ ] "How long do you typically stay logged in before having to re-enter your password?"

Record answers for later reference.

---

### Phase 2: Screenshare Setup (1 min)
- [ ] Client shares their screen (so they can see the browser we'll launch)
- [ ] OR: Set up temporary VNC/noVNC if client prefers not to screenshare
- [ ] Confirm client can see your terminal/browser window

---

### Phase 3: Run Cookie Capture (5-7 min)

#### Step 1: Start the script
```bash
cd /srv/caaa_scraper
source venv/bin/activate
python cookie_capture.py
```

#### Step 2: Browser opens automatically
- [ ] Confirm browser window appears with CAAA login page
- [ ] Client can see the page clearly

#### Step 3: Client logs in
Say to client:
> "Go ahead and log in exactly as you normally would. Take your time."

- [ ] Client enters username
- [ ] Client enters password
- [ ] Client clicks "LOGIN"
- [ ] **If MFA prompt appears**: Client completes it
- [ ] **If CAPTCHA appears**: Client solves it
- [ ] Wait for redirect to dashboard/member area

#### Step 4: Confirm success
Ask client:
> "Do you see your normal dashboard or member area now? Does everything look correct?"

- [ ] Client confirms they're logged in
- [ ] Note the URL displayed (for verification later)

#### Step 5: Capture cookies
- [ ] Press ENTER in the terminal (as instructed by the script)
- [ ] Script saves cookies and shows summary
- [ ] Browser closes automatically

---

### Phase 4: Verification (2 min)

Script will automatically reopen browser with saved cookies.

- [ ] Browser opens to CAAA site (not login page)
- [ ] Confirm: **no login prompt appears**
- [ ] Ask client: "Do you see authenticated content? Does this look like you're logged in?"
- [ ] Client confirms: yes, looks correct
- [ ] Press ENTER to close verification browser

---

### Phase 5: Encryption (1 min)

Script automatically encrypts the cookies.

- [ ] Confirm output shows:
  - ✓ Encrypted storage state saved
  - ✓ Deleted plaintext
  - ✓ Encryption key saved
- [ ] Note the file locations shown

---

### Phase 6: Post-Capture (1 min)

Say to client:
> "Perfect! We've captured your session securely. Your password was never stored—only the 'logged in' token. This will last [weeks/months], and when it expires, we'll walk through this same quick process again. You can end the screenshare now."

- [ ] Thank client
- [ ] End screenshare

---

## Post-Call Verification (Dev Only)

### 1. Verify Files Exist
```bash
ls -lh /srv/caaa_scraper/
# Should see:
# - auth.json.enc (encrypted cookies)
# - .auth_key (encryption key)
# - cookie_capture.py
```

### 2. Test Decryption
```bash
python cookie_capture.py decrypt
ls -lh auth.json  # Should exist now
```

### 3. Test Cookies in Isolation
```bash
python cookie_capture.py verify
```
- [ ] Browser opens, navigates without login prompt
- [ ] Authenticated content visible

### 4. Secure the Files
```bash
# Restrict permissions
chmod 600 .auth_key auth.json.enc
chmod 700 /srv/caaa_scraper

# Verify
ls -la
```

### 5. Document Session Info
Create a note:
```bash
cat > SESSION_INFO.md << EOF
# CAAA Session Info

**Capture Date:** $(date)
**Client Confirmed MFA:** [yes/no - fill in]
**Client Confirmed CAPTCHA:** [yes/no - fill in]
**Post-Login URL:** [fill in URL client landed on]
**Proxy IP Used:** [fill in if applicable]
**Expected Session Duration:** [fill in based on client answer]

## Next Re-Auth
Estimated: [date - weeks/months from now]
EOF
```

---

## Troubleshooting

### Problem: Browser doesn't open
**Solution:**
```bash
# Check if DISPLAY is set (needed for GUI)
echo $DISPLAY

# If empty, run Xvfb (virtual display)
sudo apt install -y xvfb
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 &
python cookie_capture.py
```

### Problem: "Redirected to login" during verification
**Causes:**
- Session expired immediately (very short timeout)
- Site detected automation
- Cookies didn't save correctly

**Solution:**
1. Try capture again with slower interaction (`slow_mo=500`)
2. Check if MFA code is tied to session
3. May need to add more realistic browser flags

### Problem: Client can't see the browser
**Solution:**
- Use noVNC for web-based browser viewing:
  ```bash
  # Install
  sudo apt install -y x11vnc novnc
  
  # Run
  x11vnc -display :99 -nopw -listen localhost -xkb &
  websockify --web /usr/share/novnc 6080 localhost:5900 &
  
  # Create SSH tunnel from client's machine:
  ssh -L 6080:localhost:6080 ubuntu@<vm-ip>
  
  # Client opens: http://localhost:6080/vnc.html
  ```

### Problem: CAPTCHA every time
**Solution:**
- Use residential proxy with consistent IP
- Ensure browser fingerprint stays identical
- May need to warm up the session (visit site a few times before login)

---

## Security Notes

### What's Stored:
- ✓ Session cookies (temporary tokens)
- ✓ localStorage (if any)
- ✗ **NOT** the password

### Encryption:
- Fernet (symmetric, AES-128)
- Key stored in `.auth_key` (600 permissions)
- Only the VM can decrypt

### Key Rotation:
- Manual for now
- When client changes password → old cookies expire → re-capture → new key generated

### Revocation:
- Client changes password → cookies invalidate immediately
- Or: delete `auth.json.enc` and `.auth_key` → session gone

---

## Timeline Estimate
| Phase | Time |
|-------|------|
| Pre-call prep (first time only) | 15-20 min |
| Client briefing | 2 min |
| Cookie capture | 5-7 min |
| Verification | 2 min |
| Wrap-up | 1 min |
| **Total call time** | **10-12 min** |

---

## Success Criteria
- [ ] `auth.json.enc` exists and is encrypted
- [ ] `.auth_key` exists with 600 permissions
- [ ] Verification shows authenticated content without login
- [ ] Client confirmed they're comfortable with the process
- [ ] Session info documented

---

## Next Steps After Capture
1. Build the scraper using `storage_state='auth.json'` in Playwright
2. Set up monitoring for session expiry (check daily)
3. Create re-auth reminder system (email/Slack)
4. Test scraper end-to-end with real search


