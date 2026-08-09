# Agent Instruction Guide: Gmail Newsletter to GitHub Pages Pipeline

## 🎯 Project Objective
Build an automated pipeline that reads unread newsletter emails from a Gmail account, parses them, converts them to Markdown, and publishes them to a GitHub repository to be rendered via GitHub Pages. The entire application must be containerized using Docker for continuous deployment.

## 📋 Phase 1: Requirements & Setup
Create a `requirements.txt` file with the following dependencies:
- `google-api-python-client`
- `google-auth-httplib2`
- `google-auth-oauthlib`
- `beautifulsoup4`
- `PyGithub`
- `schedule`
- `markdownify`

## 🔐 Phase 2: Gmail Authentication Setup (Local)
Write a one-time utility script named `auth_setup.py`.
**Goal:** Handle the initial Google OAuth2 flow, as the main app will run headlessly in Docker and cannot open a web browser.
- Load `credentials.json` (Desktop app OAuth credentials).
- Request the `https://www.googleapis.com/auth/gmail.modify` scope.
- Use `InstalledAppFlow.from_client_secrets_file` to open a local browser for auth.
- Save the resulting session token into `token.json`.

## ⚙️ Phase 3: Main Application Logic (`main.py`)
Write the core script `main.py` with the following distinct functions:

### 1. Initialize Clients
- **Gmail API:** Load `token.json` (refreshing automatically if expired) and build the `gmail` service object.
- **GitHub API:** Initialize the `Github` client using a Personal Access Token (PAT) retrieved from environment variables (`os.getenv("GITHUB_TOKEN")`).

### 2. Fetch Newsletters
- Query the Gmail API for messages matching `q="label:newsletter is:unread"`. (Note: The user will have a Gmail filter applying this label).
- Retrieve the full email payload for each matching message ID.

### 3. Parse and Convert
- Extract the HTML body of the email. Ensure the script correctly decodes both base64url encoded plain text and multipart payloads.
- Use `BeautifulSoup` to clean the HTML and extract the email's Subject line.
- Use `markdownify` to convert the cleaned HTML into standard Markdown.
- **Formatting:** Prepend Jekyll-compatible YAML front-matter to the top of the Markdown string (including `title`, `date`, and `layout`).

### 4. Publish to GitHub
- Target the configured GitHub repository (retrieved from `os.getenv("GITHUB_REPO")`, e.g., `username/daily-newsletters`).
- Create a new file in the repository under a specific directory (e.g., `_posts/YYYY-MM-DD-newsletter-subject.md`).
- Commit and push the file via the PyGithub library.

### 5. Mark as Read
- After a successful GitHub commit, use the Gmail API's `users().messages().modify()` endpoint to remove the `UNREAD` label from the processed email so it isn't picked up in the next cycle.

## 🕒 Phase 4: Scheduling & Execution
- Wrap the main processing logic in a master function (e.g., `process_inbox()`).
- Use the `schedule` library to run this function periodically (e.g., `schedule.every(4).hours.do(process_inbox)`).
- Implement a `while True:` loop with `time.sleep(60)` to keep the script running indefinitely. 
- **Crucial:** Implement robust try/except blocks inside the scheduled job so that temporary network errors or malformed emails do not crash the container.

## 🐳 Phase 5: Dockerization
Create a `Dockerfile` with the following specifications:
- **Base Image:** `python:3.11-slim`
- **Working Directory:** `/app`
- **Copy Files:** Copy `requirements.txt` and `main.py` into the container. 
- **Volumes Note:** Add a comment noting that `token.json` and `credentials.json` should be mounted via volumes at runtime, rather than baked into the image.
- **Install Dependencies:** `RUN pip install --no-cache-dir -r requirements.txt`
- **Execution:** `CMD ["python", "-u", "main.py"]` (The `-u` flag is mandatory for unbuffered stdout to ensure Python print statements appear in Docker logs).

## 🚀 Expected Output Files
Please generate the following files based on these instructions:
1. `requirements.txt`
2. `auth_setup.py`
3. `main.py`
4. `Dockerfile`
