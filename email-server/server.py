import asyncio
import os
import base64
from email.mime.text import MIMEText
from typing import Any, Dict, List
from email.mime.multipart import MIMEMultipart
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class MinimalEmailServer:
    def __init__(self):
        self.server = Server("minimal-email-server")
        self.service = None
        self.credentials = None
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly'
        ]
        self.initialize_service()
        self.setup_tools()

    def initialize_service(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        token_path = os.path.join(script_dir, 'token.json')
        # credentials_path = os.path.join(script_dir, 'credentials.json')
        self.credentials = Credentials.from_authorized_user_file(token_path, self.SCOPES)
        self.service = build('gmail', 'v1', credentials=self.credentials)

    def setup_tools(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="send_email",
                    description="Send an email via Gmail",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "body": {"type": "string", "description": "Email body content"},
                            "cc": {"type": "string", "description": "CC recipients (comma-separated)"},
                            "bcc": {"type": "string", "description": "BCC recipients (comma-separated)"},
                            "is_html": {"type": "boolean", "description": "Whether the body is HTML", "default": False}
                        },
                        "required": ["to", "subject", "body"]
                    }
                ),
                Tool(
                    name="list_emails",
                    description="List recent emails",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "max_results": {"type": "integer", "description": "Maximum number of emails to return", "default": 10},
                            "query": {"type": "string", "description": "Gmail search query (e.g., 'from:example@gmail.com')"}
                        }
                    }
                ),
                Tool(
                    name="get_email",
                    description="Get details of a specific email",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {"type": "string", "description": "Message ID"}
                        },
                        "required": ["message_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "send_email":
                    return await self.send_email(arguments)
                elif name == "list_emails":
                    return await self.list_emails(arguments)
                elif name == "get_email":
                    return await self.get_email(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def create_message(self, to: str = '', subject: str = '', body: str = '', cc: str = '', bcc: str = '', is_html: bool = False):
        message = MIMEMultipart() if cc or bcc else MIMEText(body, 'html' if is_html else 'plain')
        if isinstance(message, MIMEMultipart):
            message.attach(MIMEText(body, 'html' if is_html else 'plain'))
        message['to'] = to
        message['subject'] = subject
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

    async def send_email(self, args: Dict[str, Any]) -> List[TextContent]:
        if not self.service:
            return [TextContent(type="text", text="Gmail service is not initialized. Please check authentication.")]
        to = args.get('to') or ''
        subject = args.get('subject') or ''
        body = args.get('body') or ''
        cc = args.get('cc') or ''
        bcc = args.get('bcc') or ''
        is_html = args.get('is_html', False)
        try:
            message = self.create_message(to, subject, body, cc, bcc, is_html)
            result = self.service.users().messages().send(userId='me', body=message).execute()
            return [TextContent(type="text", text=f"Email sent successfully! Message ID: {result['id']}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to send email: {str(e)}")]

    async def list_emails(self, args: Dict[str, Any]) -> List[TextContent]:
        if not self.service:
            return [TextContent(type="text", text="Gmail service is not initialized. Please check authentication.")]
        max_results = args.get('max_results', 10)
        query = args.get('query', '')
        try:
            results = self.service.users().messages().list(userId='me', maxResults=max_results, q=query).execute()
            messages = results.get('messages', [])
            if not messages:
                return [TextContent(type="text", text="No emails found.")]
            email_list = []
            for msg in messages:
                message = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                from_addr = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown Sender)')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '(No Date)')
                email_list.append(f"- {subject} | From: {from_addr} | Date: {date} | ID: {msg['id']}")
            return [TextContent(type="text", text=f"Recent emails:\n" + '\n'.join(email_list))]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to list emails: {str(e)}")]

    async def get_email(self, args: Dict[str, Any]) -> List[TextContent]:
        if not self.service:
            return [TextContent(type="text", text="Gmail service is not initialized. Please check authentication.")]
        message_id = args.get('message_id')
        try:
            message = self.service.users().messages().get(userId='me', id=message_id).execute()
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
            from_addr = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown Sender)')
            to_addr = next((h['value'] for h in headers if h['name'] == 'To'), '(No Recipient)')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '(No Date)')
            body = ""
            payload = message['payload']
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
            else:
                if payload['mimeType'] == 'text/plain':
                    data = payload['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            return [TextContent(
                type="text",
                text=f"Email Details:\n"
                     f"Subject: {subject}\n"
                     f"From: {from_addr}\n"
                     f"To: {to_addr}\n"
                     f"Date: {date}\n\n"
                     f"Body:\n{body}"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to get email: {str(e)}")]

async def main():
    server = MinimalEmailServer()
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main()) 