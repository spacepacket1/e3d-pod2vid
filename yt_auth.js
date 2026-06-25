#!/usr/bin/env node
/**
 * yt_auth.js  —  e3d-pod2vid
 *
 * Headless YouTube OAuth2 flow (no browser required on this machine).
 * Works on servers, VMs, or any machine where opening a browser isn't possible.
 *
 * Usage:
 *   node yt_auth.js
 *
 * The script prints an authorization URL. Open it on any device (phone, laptop).
 * After approving, paste the redirect URL (starts with http://localhost:8080/?code=...)
 * back into this terminal. Tokens are saved to youtube-tokens.json.
 *
 * Requires:
 *   youtube-client-secret.json  — download from Google Cloud Console
 *     (APIs & Services > Credentials > OAuth 2.0 Client IDs > Download JSON)
 *
 * Scopes granted:
 *   https://www.googleapis.com/auth/youtube  (full access: upload + update + thumbnail)
 */

'use strict';
require('dotenv').config();

const fs      = require('fs');
const path    = require('path');
const https   = require('https');
const readline = require('readline');
const { URLSearchParams } = require('url');

const SECRET_FILE = process.env.YT_CLIENT_SECRET || 'youtube-client-secret.json';
const TOKEN_FILE  = process.env.YT_TOKEN_FILE    || 'youtube-tokens.json';
const REDIRECT    = 'http://localhost:8080';
const SCOPE       = 'https://www.googleapis.com/auth/youtube';

function post(url, params) {
  return new Promise((resolve, reject) => {
    const body = new URLSearchParams(params).toString();
    const opts = Object.assign(require('url').parse(url), {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded',
                 'Content-Length': Buffer.byteLength(body) },
    });
    const req = https.request(opts, res => {
      let data = '';
      res.on('data', d => (data += d));
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch { reject(new Error(data)); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function run() {
  if (!fs.existsSync(SECRET_FILE)) {
    console.error(`Error: ${SECRET_FILE} not found.`);
    console.error('Download it from Google Cloud Console:');
    console.error('  APIs & Services > Credentials > OAuth 2.0 Client IDs > Download JSON');
    process.exit(1);
  }

  const raw    = JSON.parse(fs.readFileSync(SECRET_FILE));
  const creds  = raw.installed || raw.web;
  const cid    = creds.client_id;
  const secret = creds.client_secret;

  const authUrl = 'https://accounts.google.com/o/oauth2/v2/auth?' + new URLSearchParams({
    client_id:     cid,
    redirect_uri:  REDIRECT,
    response_type: 'code',
    scope:         SCOPE,
    access_type:   'offline',
    prompt:        'consent',
  });

  console.log('\n──────────────────────────────────────────────────────');
  console.log('Open this URL on any device (phone, browser, laptop):');
  console.log();
  console.log(authUrl);
  console.log();
  console.log('After approving, you will be redirected to localhost:8080.');
  console.log('The page will fail to load — that is expected.');
  console.log('Copy the full URL from your browser address bar and paste it here:');
  console.log('──────────────────────────────────────────────────────\n');

  const rl   = readline.createInterface({ input: process.stdin });
  const line = await new Promise(r => rl.once('line', r));
  rl.close();

  let code;
  try {
    code = new URL(line).searchParams.get('code');
  } catch {
    // handle bare code
    code = line.trim();
  }
  if (!code) { console.error('Could not extract code from URL'); process.exit(1); }

  console.log('\nExchanging code for tokens...');
  const tokens = await post('https://oauth2.googleapis.com/token', {
    code, client_id: cid, client_secret: secret,
    redirect_uri: REDIRECT, grant_type: 'authorization_code',
  });

  if (tokens.error) {
    console.error('Token exchange failed:', JSON.stringify(tokens, null, 2));
    process.exit(1);
  }

  tokens.expiry_date = Date.now() + (tokens.expires_in || 3600) * 1000;
  fs.writeFileSync(TOKEN_FILE, JSON.stringify(tokens, null, 2));
  console.log(`\nTokens saved to ${TOKEN_FILE}`);
  console.log('Scopes:', tokens.scope);
  console.log('Run "node yt_upload.js <video.mp4> <title>" to upload.');
}

run().catch(err => { console.error(err.message || err); process.exit(1); });
