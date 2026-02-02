const fs = require('fs').promises;
const path = require('path');
const { google } = require('googleapis');
const { authenticate } = require('@google-cloud/local-auth');

// Configuration
const SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
];
const TOKEN_PATH = path.join(__dirname, '../token.json');
const CREDENTIALS_PATH = path.join(__dirname, '../credentials.json');
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

// Logging Helper
async function logWork(status, details) {
    const date = new Date().toISOString().split('T')[0];
    const logFile = path.join(__dirname, `../obsidian_vault/03_Logs/Work_Logs/${date}_Gmail_Check.md`);
    const content = `
# Work Log: Gmail Check

## 📅 Basic Info
- **Time:** ${new Date().toISOString()}
- **Model:** gemini-2.0-flash
- **Status:** ${status}

## 📝 Details
${details}
`;
    await fs.appendFile(logFile, content);
}

// Load Credentials
async function loadSavedCredentialsIfExist() {
    try {
        const content = await fs.readFile(CREDENTIALS_PATH);
        const keys = JSON.parse(content);
        const key = keys.installed || keys.web;
        const client = new google.auth.OAuth2(
            key.client_id,
            key.client_secret,
            key.redirect_uris[0]
        );
        const token = await fs.readFile(TOKEN_PATH);
        client.setCredentials(JSON.parse(token));

        // Auto-save refreshed tokens
        client.on('tokens', async (tokens) => {
            try {
                const currentToken = JSON.parse(await fs.readFile(TOKEN_PATH));
                const newTokens = { ...currentToken, ...tokens };
                await fs.writeFile(TOKEN_PATH, JSON.stringify(newTokens));
                console.log('Updated tokens saved to token.json');
            } catch (err) {
                console.error('Failed to save refreshed tokens:', err);
            }
        });

        return client;
    } catch (err) {
        console.error('Failed to load token:', err);
        return null;
    }
}

async function saveCredentials(client) {
    const content = await fs.readFile(CREDENTIALS_PATH);
    const keys = JSON.parse(content);
    const key = keys.installed || keys.web;
    const payload = JSON.stringify({
        type: 'authorized_user',
        client_id: key.client_id,
        client_secret: key.client_secret,
        refresh_token: client.credentials.refresh_token,
    });
    await fs.writeFile(TOKEN_PATH, payload);
}

// Gemini Parse
async function parseEmailWithGemini(subject, body) {
    if (!GEMINI_API_KEY) return null;

    const prompt = `
    Analyze this email. Is it a request/task/meeting for me?
    Subject: ${subject}
    Body: ${body}
    
    If yes, return JSON: {
        "is_task": true, 
        "summary": "Task/Meeting Summary", 
        "start_datetime": "YYYY-MM-DDTHH:mm:00 (ISO format if time specified, else YYYY-MM-DD for all day)",
        "end_datetime": "YYYY-MM-DDTHH:mm:00 (If unknown, +1 hour from start)",
        "requester": "Name"
    }
    If no, return JSON: {"is_task": false}
    Return ONLY JSON.
  `;

    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
    });

    const data = await response.json();
    try {
        const text = data.candidates[0].content.parts[0].text;
        const jsonStr = text.replace(/```json/g, '').replace(/```/g, '').trim();
        return JSON.parse(jsonStr);
    } catch (e) {
        return { is_task: false };
    }
}

// Main Logic
async function main() {
    let auth = await loadSavedCredentialsIfExist();
    if (!auth) {
        console.log('Token missing. Please run setup_auth.js first.');
        await logWork('Failure', 'Token missing. Authentication required.');
        return;
    }

    const gmail = google.gmail({ version: 'v1', auth });
    const calendar = google.calendar({ version: 'v3', auth });

    try {
        // 1. List Unread Emails (last 1h)
        const res = await gmail.users.messages.list({
            userId: 'me',
            q: 'is:unread newer_than:1h'
        });

        const messages = res.data.messages || [];
        let logDetails = `Checked ${messages.length} messages.\n`;

        if (messages.length === 0) {
            console.log('No new messages.');
            await logWork('Success', 'No emails found.');
            return;
        }

        for (const msg of messages) {
            const m = await gmail.users.messages.get({ userId: 'me', id: msg.id });
            const subject = m.data.payload.headers.find(h => h.name === 'Subject')?.value;
            const snippet = m.data.snippet;

            // Parse
            const analysis = await parseEmailWithGemini(subject, snippet);

            if (analysis && analysis.is_task) {
                // Construct Event Resource
                const eventResource = {
                    summary: `[ClawdBot] ${analysis.summary}`,
                    description: `Requester: ${analysis.requester}\nSource: Gmail\nOriginal Subject: ${subject}`,
                };

                // Handle Date vs DateTime
                if (analysis.start_datetime && analysis.start_datetime.includes('T')) {
                    // Time specified
                    eventResource.start = { dateTime: analysis.start_datetime, timeZone: 'Asia/Tokyo' };
                    eventResource.end = { dateTime: analysis.end_datetime || analysis.start_datetime, timeZone: 'Asia/Tokyo' };
                } else {
                    // All day
                    const dateStr = analysis.start_datetime || new Date().toISOString().split('T')[0];
                    eventResource.start = { date: dateStr };
                    eventResource.end = { date: dateStr };
                }

                // Add to Calendar
                await calendar.events.insert({
                    calendarId: 'primary',
                    requestBody: eventResource
                });
                logDetails += `- Added task: ${analysis.summary} (${analysis.start_datetime})\n`;
            } else {
                logDetails += `- Skipped: ${subject}\n`;
            }
        }

        await logWork('Success', logDetails);

    } catch (error) {
        console.error(error);
        await logWork('Failure', error.message);
    }
}

main();
