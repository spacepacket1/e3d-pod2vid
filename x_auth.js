#!/usr/bin/env node
/**
 * x_auth.js  —  e3d-pod2vid
 *
 * Headless X (Twitter) OAuth2 PKCE flow. No browser required on this machine.
 *
 * Usage:
 *   node x_auth.js
 *
 * The script prints an authorization URL. Open it on any device (phone, laptop).
 * After approving, you will be redirected to http://localhost:8080/?code=...
 * The page will fail to load — that is expected.
 * Paste the full redirect URL back into this terminal.
 * Tokens are saved to x-oauth2-tokens.json (update X_TOKEN_FILE in .env if needed).
 *
 * Required env vars (in .env):
 *   X_CLIENT_ID      OAuth2 client ID
 *   X_CLIENT_SECRET  OAuth2 client secret
 *
 * Scopes: tweet.read tweet.write users.read offline.access media.write
 */

'use strict';
require('dotenv').config();

const fs       = require('fs');
const https    = require('https');
const crypto   = require('crypto');
const readline = require('readline');
const { URLSearchParams } = require('url');

const CLIENT_ID     = process.env.X_CLIENT_ID;
const CLIENT_SECRET = process.env.X_CLIENT_SECRET;
const TOKEN_FILE    = process.env.X_TOKEN_FILE || 'x-oauth2-tokens.json';
const REDIRECT_URI  = 'http://localhost:8080';
const SCOPE         = 'tweet.read tweet.write users.read offline.access media.write';

function base64url(buf) {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

function post(url, params, authHeader) {
  return new Promise((resolve, reject) => {
    const body = new URLSearchParams(params).toString();
    const u    = new URL(url);
    const req  = https.request({
      hostname: u.hostname, path: u.pathname, port: 443,
      method: 'POST',
      headers: Object.assign({
        'Content-Type':   'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(body),
      }, authHeader ? { Authorization: authHeader } : {}),
    }, res => {
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
  if (!CLIENT_ID || !CLIENT_SECRET) {
    console.error('Error: X_CLIENT_ID and X_CLIENT_SECRET must be set in .env');
    process.exit(1);
  }

  // PKCE
  const codeVerifier  = base64url(crypto.randomBytes(32));
  const codeChallenge = base64url(crypto.createHash('sha256').update(codeVerifier).digest());
  const state         = base64url(crypto.randomBytes(16));

  const authUrl = 'https://twitter.com/i/oauth2/authorize?' + new URLSearchParams({
    response_type:         'code',
    client_id:             CLIENT_ID,
    redirect_uri:          REDIRECT_URI,
    scope:                 SCOPE,
    state,
    code_challenge:        codeChallenge,
    code_challenge_method: 'S256',
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
    const parsed = new URL(line.trim());
    code = parsed.searchParams.get('code');
    const returnedState = parsed.searchParams.get('state');
    if (returnedState !== state) console.warn('Warning: state mismatch — proceed with caution');
  } catch {
    code = line.trim();
  }
  if (!code) { console.error('Could not extract code from URL'); process.exit(1); }

  console.log('\nExchanging code for tokens...');
  const auth   = Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString('base64');
  const tokens = await post('https://api.twitter.com/2/oauth2/token', {
    grant_type:    'authorization_code',
    code,
    redirect_uri:  REDIRECT_URI,
    code_verifier: codeVerifier,
  }, `Basic ${auth}`);

  if (tokens.error) {
    console.error('Token exchange failed:', JSON.stringify(tokens, null, 2));
    process.exit(1);
  }

  tokens.expires_at = Date.now() + (tokens.expires_in || 7200) * 1000;
  tokens.client_id  = CLIENT_ID;
  fs.writeFileSync(TOKEN_FILE, JSON.stringify(tokens, null, 2));

  console.log(`\nTokens saved to ${TOKEN_FILE}`);
  console.log(`access_token expires in ${Math.round((tokens.expires_in || 7200) / 60)} minutes`);
  console.log(`refresh_token: ${tokens.refresh_token ? 'present ✓' : 'NOT present (offline.access scope may not be enabled for this app)'}`);
  console.log('\nUpdate X_TOKEN_FILE in .env if needed, then re-run announce.js.');
}

run().catch(err => { console.error(err.message || err); process.exit(1); });
