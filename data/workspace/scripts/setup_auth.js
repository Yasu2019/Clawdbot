const fs = require('fs').promises;
const path = require('path');
const { google } = require('googleapis');
const readline = require('readline');

// Config
const SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar'
];
const TOKEN_PATH = path.join(__dirname, '../token.json');
const CREDENTIALS_PATH = path.join(__dirname, '../credentials.json');

async function main() {
    let content;
    try {
        content = await fs.readFile(CREDENTIALS_PATH);
    } catch (err) {
        console.log('Error loading credentials.json:', err);
        console.log('Please save your OAuth Client ID JSON file as "data/workspace/credentials.json"');
        return;
    }

    const keys = JSON.parse(content);
    const key = keys.installed || keys.web;
    const client = new google.auth.OAuth2(
        key.client_id,
        key.client_secret,
        'http://localhost'
    );

    const authUrl = client.generateAuthUrl({
        access_type: 'offline',
        scope: SCOPES,
    });

    console.log('Authorize this app by visiting this url:', authUrl);

    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });

    rl.question('Enter the code from that page here: ', async (code) => {
        rl.close();
        const { tokens } = await client.getToken(code);
        client.setCredentials(tokens);
        await fs.writeFile(TOKEN_PATH, JSON.stringify(tokens));
        console.log('Token stored to', TOKEN_PATH);
        console.log('Setup Complete! You can now verify by running: node gmail_to_calendar.js');
    });
}

main();
