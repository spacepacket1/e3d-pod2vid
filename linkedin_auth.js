#!/usr/bin/env node
/**
 * linkedin_auth.js  —  e3d-pod2vid
 *
 * Headless LinkedIn OAuth2 flow. No browser required on this machine.
 *
 * Usage:
 *   node linkedin_auth.js
 *
 * Saves tokens to linkedin-tokens.json.
 * Required scopes: openid profile w_member_social
 */

'use strict';
require('dotenv').config();

const fs       = require('fs');
const https    = require('https');
const readline = require('readline');
const { URLSearchParams } = require('url');

const CLIENT_ID     = process.env.LINKEDIN_CLIENT_ID;
const CLIENT_SECRET = process.env.LINKEDIN_CLIENT_SECRET;
const REDIRECT_URI  = process.env.LINKEDIN_REDIRECT_URI  || 'https://www.linkedin.com/developers/tools/oauth/redirect';
const TOKEN_FILE    = process.env.LINKEDIN_TOKEN_FILE    || 'linkedin-tokens.json';
const SCOPE         = 'openid profile w_member_social';

function post(url, params) {
  return new Promise((resolve, reject) => {
    const body = new URLSearchParams(params).toString();
    const u    = require('url').parse(url);
    const req  = https.request(Object.assign(u, {
      method: 'POST',
      headers: {
        'Content-Type':   'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(body),
      },
    }), res => {
      let data = '';
      res.on('data', d => (data += d));
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function run() {
  if (!CLIENT_ID || !CLIENT_SECRET) {
    console.error('Error: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env');
    process.exit(1);
  }
  const authUrl = 'https://www.linkedin.com/oauth/v2/authorization?' + new URLSearchParams({
    response_type: 'code',
    client_id:     CLIENT_ID,
    redirect_uri:  REDIRECT_URI,
    scope:         SCOPE,
    state:         'pod2vid',
  });

  console.log('\n──────────────────────────────────────────────────────');
  console.log('Open this URL on any device (phone, browser, laptop):');
  console.log();
  console.log(authUrl);
  console.log();
  console.log('After approving, LinkedIn will show you the authorization code.');
  console.log('Paste it here (just the code, or the full URL):');
  console.log('──────────────────────────────────────────────────────\n');

  const rl   = readline.createInterface({ input: process.stdin });
  const line = await new Promise(r => rl.once('line', r));
  rl.close();

  let code;
  try { code = new URL(line.trim()).searchParams.get('code'); }
  catch { code = line.trim(); }
  if (!code) { console.error('Could not extract code'); process.exit(1); }

  console.log('Exchanging code for tokens...');
  const res = await post('https://www.linkedin.com/oauth/v2/accessToken', {
    grant_type:    'authorization_code',
    code,
    redirect_uri:  REDIRECT_URI,
    client_id:     CLIENT_ID,
    client_secret: CLIENT_SECRET,
  });

  if (res.body.error || !res.body.access_token) {
    console.error('Token exchange failed:', JSON.stringify(res.body, null, 2));
    process.exit(1);
  }

  res.body.expiry_date = Date.now() + (res.body.expires_in || 5183944) * 1000;
  fs.writeFileSync(TOKEN_FILE, JSON.stringify(res.body, null, 2));
  console.log(`\nTokens saved to ${TOKEN_FILE}`);
  console.log(`Expires: ${new Date(res.body.expiry_date).toDateString()}`);
}

run().catch(err => { console.error(err.message || err); process.exit(1); });
