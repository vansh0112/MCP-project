# Calendar Server (Google Calendar MCP Integration)

This project provides an MCP-compatible server for interacting with Google Calendar and Gmail via the Google API. You can add, list, update, and delete calendar events using natural language queries or tool calls.

---

## Features
- Add events to your Google Calendar
- List upcoming events
- Update or delete existing events
- Send and list emails via Gmail
- Supports timezones (default: Asia/Kolkata for IST)

---

## Prerequisites
- Python 3.8+
- A Google Cloud project with Calendar API and Gmail API enabled
- `credentials.json` (OAuth client credentials) downloaded from Google Cloud Console

---

## Setup Instructions

### 1. Clone the repository
```sh
# Example
cd /path/to/your/workspace
```

### 2. Install dependencies
```sh
pip install -r requirements.txt
```

### 3. Google Cloud Setup
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project (or use an existing one)
- Enable the **Google Calendar API** and **Gmail API**
- Go to **APIs & Services > Credentials**
- Create **OAuth client ID** credentials (Desktop app)
- Download the `credentials.json` file and place it in the `calendar-server/` and `email-server/` directory

### 4. Authenticate (First Run)
- Before running the server for the first time, you must authenticate with Google to generate `token.json`.
- Run the following command in the `calendar-server` and `email-server/`directory:
  ```sh
  python auth.py
  ```
- This will open a browser window for you to log in and authorize access.
- After successful authentication, a `token.json` file will be created and used by the server.

### 5. Run the Server with Claude Desktop

If you are integrating this server with Claude Desktop, you need to configure it using a `claude_desktop_config.json` file. Below is an example configuration:

```json
{
  "mcpServers": {
    "calendar": {
      "command": "path/to/your/python.exe",
      "args": ["path/to/your/server.py"]
    },
    "email":{
      "command": "path/to/your/python.exe",
      "args": ["path/to/your/server.py"]
    }
  }
}
```


- Start Claude Desktop. It will launch the server as configured and allow you to interact with your Google Calendar and Gmail through the Claude Desktop interface.

---

## Calendar Commands 

- "Create a calendar event for tomorrow at 2 PM called 'Team Meeting'"
- "List my upcoming calendar events"

---

## Combined Workflow Example

Try this combined workflow:

- Create a calendar event for next Monday at 10 AM called "Project Kickoff" with description "Initial project meeting with the team" and invite example1@example.com and example2@example.com. Then send an email to both attendees with the meeting details.

---
## Troubleshooting

- **Timezone Issues:**
  - Always use a valid IANA timezone string (e.g., `Asia/Kolkata`).
  - If you get errors with timezones, try re-authenticating (delete `token.json` and rerun).

- **Authorization Errors:**
  - Ensure `credentials.json` is present and valid.
  - Delete `token.json` and re-authenticate if you change scopes or Google account.



---

 