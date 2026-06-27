#!/usr/bin/env node
/**
 * announce.js  —  e3d-pod2vid
 *
 * Posts a YouTube video URL to all configured social platforms simultaneously.
 * Each platform is optional — configure only what you have.
 *
 * Usage:
 *   node announce.js <youtube-url> [custom message]
 *
 * Environment variables:
 *   DISCORD_BOT_TOKEN     bot token (starts with MTU...)
 *   DISCORD_CHANNEL_ID    target channel numeric ID
 *
 *   TELEGRAM_BOT_TOKEN    format: 1234567890:AAF...
 *   TELEGRAM_CHAT_ID      numeric chat/channel ID (negative for groups/channels)
 *
 *   X_ACCESS_TOKEN        OAuth2 access token
 *   X_ACCESS_SECRET       (OAuth1 legacy — leave blank if using OAuth2 only)
 *
 *   MOLTBOOK_API_KEY      format: moltbook_sk_...
 *   MOLTBOOK_API_URL      (default: https://moltbook.com)
 */

'use strict';
require('dotenv').config();

const https  = require('https');
const { URL } = require('url');

const YT_URL = process.argv[2];
const CUSTOM = process.argv[3] || '';

if (!YT_URL) {
  console.error('Usage: node announce.js <youtube-url> [message]');
  process.exit(1);
}

// ── HTTP helper ───────────────────────────────────────────────────────────────

function post(url, opts, payload) {
  return new Promise((resolve, reject) => {
    const u   = new URL(url);
    const body = typeof payload === 'string' ? payload : JSON.stringify(payload);
    const req = https.request({
      hostname: u.hostname, path: u.pathname + u.search, port: 443,
      method: 'POST',
      headers: Object.assign({
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      }, opts.headers || {}),
    }, res => {
      let data = '';
      res.on('data', d => (data += d));
      res.on('end', () => resolve({ status: res.statusCode, body: data }));
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── Platforms ─────────────────────────────────────────────────────────────────

async function postDiscord(url, message) {
  const token   = process.env.DISCORD_BOT_TOKEN;
  const channel = process.env.DISCORD_CHANNEL_ID;
  if (!token || !channel) return { platform: 'Discord', skipped: true };
  const res = await post(
    `https://discord.com/api/v10/channels/${channel}/messages`,
    { headers: { Authorization: `Bot ${token}` } },
    { content: message },
  );
  return { platform: 'Discord', status: res.status, ok: res.status === 200 };
}

async function postTelegram(url, message) {
  const token  = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) return { platform: 'Telegram', skipped: true };
  const res = await post(
    `https://api.telegram.org/bot${token}/sendMessage`,
    {},
    { chat_id: chatId, text: message, parse_mode: 'Markdown' },
  );
  const body = JSON.parse(res.body);
  return { platform: 'Telegram', status: res.status, ok: body.ok };
}

async function postX(url, message) {
  const token = process.env.X_ACCESS_TOKEN;
  if (!token) return { platform: 'X (Twitter)', skipped: true };
  const tweet = message.length <= 280 ? message : message.slice(0, 277) + '...';
  const res = await post(
    'https://api.twitter.com/2/tweets',
    { headers: { Authorization: `Bearer ${token}` } },
    { text: tweet },
  );
  const body = JSON.parse(res.body);
  return { platform: 'X (Twitter)', status: res.status, ok: !!body.data?.id };
}

async function postLinkedIn(url, message) {
  const tokenFile = process.env.LINKEDIN_TOKEN_FILE || 'linkedin-tokens.json';
  if (!require('fs').existsSync(tokenFile)) return { platform: 'LinkedIn', skipped: true };
  const tokens = JSON.parse(require('fs').readFileSync(tokenFile));
  if (!tokens.access_token) return { platform: 'LinkedIn', skipped: true };
  const author = tokens.person_urn;
  if (!author) return { platform: 'LinkedIn', skipped: true, reason: 'no person_urn in token file' };
  const payload = JSON.stringify({
    author,
    commentary: message,
    visibility: 'PUBLIC',
    distribution: { feedDistribution: 'MAIN_FEED', targetEntities: [], thirdPartyDistributionChannels: [] },
    lifecycleState: 'PUBLISHED',
    isReshareDisabledByAuthor: false,
  });
  const res = await post('https://api.linkedin.com/rest/posts', {
    headers: {
      'Authorization':    `Bearer ${tokens.access_token}`,
      'LinkedIn-Version': '202506',
      'X-Restli-Protocol-Version': '2.0.0',
    },
  }, payload);
  return { platform: 'LinkedIn', status: res.status, ok: res.status === 201 };
}

async function postMoltbook(url, message) {
  const key      = process.env.MOLTBOOK_API_KEY;
  const apiUrl   = process.env.MOLTBOOK_API_URL || 'https://www.moltbook.com/api/v1';
  const submolt  = process.env.MOLTBOOK_SUBMOLT || 'agentfinance';
  const title    = process.env.MOLTBOOK_TITLE   || message.split('\n')[0].slice(0, 300);
  if (!key) return { platform: 'Moltbook', skipped: true };
  const res = await post(
    `${apiUrl}/posts`,
    { headers: { 'x-api-key': key } },
    { title, content: message, submolt_name: submolt, type: 'text' },
  );
  return { platform: 'Moltbook', status: res.status, ok: res.status === 200 || res.status === 201 };
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function run() {
  const message = CUSTOM || `New video: ${YT_URL}`;

  console.log(`Announcing to social platforms...`);
  console.log(`Message: ${message.slice(0, 80)}${message.length > 80 ? '...' : ''}\n`);

  const results = await Promise.allSettled([
    postDiscord(YT_URL, message),
    postTelegram(YT_URL, message),
    postX(YT_URL, message),
    postMoltbook(YT_URL, message),
    postLinkedIn(YT_URL, message),
  ]);

  for (const r of results) {
    if (r.status === 'fulfilled') {
      const { platform, skipped, ok, status } = r.value;
      if (skipped) {
        console.log(`  ${platform}: skipped (no credentials configured)`);
      } else if (ok) {
        console.log(`  ${platform}: posted ✓`);
      } else {
        console.log(`  ${platform}: FAILED (HTTP ${status})`);
      }
    } else {
      console.log(`  ERROR: ${r.reason?.message || r.reason}`);
    }
  }
}

run().catch(err => { console.error('Error:', err.message || err); process.exit(1); });
