#!/usr/bin/env node
/**
 * announce.js  —  e3d-pod2vid
 *
 * Posts to all configured social platforms simultaneously. Each platform is
 * optional — configure only what you have.
 *
 * Usage:
 *   node announce.js <youtube-url> [custom message] [video-file-path]
 *
 * When video-file-path is given, Discord and Telegram get the actual video
 * file attached natively (people watch inline, no click-through to YouTube)
 * instead of just a link. X, Moltbook, and LinkedIn still get the YouTube
 * link — X's video upload needs a separate chunked media-upload flow and
 * elevated API access, LinkedIn's needs a video-specific product grant
 * beyond the basic "Share on LinkedIn" scope this app has, and Moltbook's
 * API is text/link-only. All of them still get the YouTube link either way,
 * since it stays the durable, searchable home for the video regardless of
 * what else it's cross-posted to.
 *
 * Discord's free-tier upload cap is 20MB (as of the Aug 2026 change) unless
 * the server has boosts; Telegram's Bot API cap is 50MB. A file over either
 * limit falls back to a link-only post on that platform rather than failing
 * the whole announcement.
 *
 * Environment variables:
 *   X_MESSAGE             optional override of the post text used only for X,
 *                         e.g. a shorter variant to fit under 280 chars
 *
 *   DISCORD_BOT_TOKEN     bot token (starts with MTU...)
 *   DISCORD_CHANNEL_ID    target channel numeric ID
 *
 *   TELEGRAM_BOT_TOKEN    format: 1234567890:AAF...
 *   TELEGRAM_CHAT_ID      numeric chat/channel ID (negative for groups/channels)
 *
 *   X_CLIENT_ID           OAuth2 client ID (needed for token refresh)
 *   X_CLIENT_SECRET       OAuth2 client secret (needed for token refresh)
 *   X_ACCESS_TOKEN        OAuth2 access token (auto-refreshed if X_CLIENT_ID/SECRET set)
 *   X_TOKEN_FILE          path to token file for refresh (default: agents/scripts/x-oauth2-tokens.json)
 *
 *   MOLTBOOK_API_KEY      format: moltbook_sk_...
 *   MOLTBOOK_API_URL      (default: https://moltbook.com)
 */

'use strict';
require('dotenv').config();

const fs     = require('fs');
const https  = require('https');
const { URL, URLSearchParams } = require('url');

const YT_URL     = process.argv[2];
const CUSTOM     = process.argv[3] || '';
const VIDEO_PATH = process.argv[4] || '';

if (!YT_URL) {
  console.error('Usage: node announce.js <youtube-url> [message] [video-file-path]');
  process.exit(1);
}

if (VIDEO_PATH && !fs.existsSync(VIDEO_PATH)) {
  console.error(`Video file not found: ${VIDEO_PATH}`);
  process.exit(1);
}

// ── HTTP helpers ─────────────────────────────────────────────────────────────

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

// Minimal hand-rolled multipart/form-data encoder - no npm dependency for
// this beyond what's already in package.json (just dotenv). `fields` is an
// ordered list of either {name, value} (plain text field) or
// {name, filename, contentType, data} (file field, data is a Buffer).
function postMultipart(url, opts, fields) {
  return new Promise((resolve, reject) => {
    const boundary = `----e3dpod2vid${Date.now()}${Math.random().toString(16).slice(2)}`;
    const parts = [];
    for (const field of fields) {
      if (field.filename) {
        parts.push(Buffer.from(
          `--${boundary}\r\nContent-Disposition: form-data; name="${field.name}"; filename="${field.filename}"\r\nContent-Type: ${field.contentType || 'application/octet-stream'}\r\n\r\n`,
        ));
        parts.push(field.data);
        parts.push(Buffer.from('\r\n'));
      } else {
        parts.push(Buffer.from(
          `--${boundary}\r\nContent-Disposition: form-data; name="${field.name}"\r\n\r\n${field.value}\r\n`,
        ));
      }
    }
    parts.push(Buffer.from(`--${boundary}--\r\n`));
    const body = Buffer.concat(parts);

    const u = new URL(url);
    const req = https.request({
      hostname: u.hostname, path: u.pathname + u.search, port: 443,
      method: 'POST',
      headers: Object.assign({
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': body.length,
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

// ── X token refresh ───────────────────────────────────────────────────────────

async function getXToken() {
  const envToken    = process.env.X_ACCESS_TOKEN;
  const clientId    = process.env.X_CLIENT_ID;
  const clientSecret= process.env.X_CLIENT_SECRET;
  const tokenFile   = process.env.X_TOKEN_FILE || null;

  // Load token file if present (has expiry + refresh_token)
  let stored = null;
  if (tokenFile && fs.existsSync(tokenFile)) {
    try { stored = JSON.parse(fs.readFileSync(tokenFile)); } catch {}
  }

  const expires = stored?.expires_at || 0;
  const needsRefresh = expires && expires < Date.now() + 60_000;

  if (needsRefresh && stored?.refresh_token && clientId && clientSecret) {
    const body = new URLSearchParams({
      grant_type:    'refresh_token',
      refresh_token: stored.refresh_token,
      client_id:     clientId,
    }).toString();
    const auth = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
    const res  = await post('https://api.twitter.com/2/oauth2/token',
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded', Authorization: `Basic ${auth}` } },
      body,
    );
    const r = JSON.parse(res.body);
    if (r.access_token) {
      r.expires_at = Date.now() + (r.expires_in || 7200) * 1000;
      r.client_id  = clientId;
      if (tokenFile) fs.writeFileSync(tokenFile, JSON.stringify(r, null, 2));
      // Update process.env so the new token is used if called again
      process.env.X_ACCESS_TOKEN = r.access_token;
      return r.access_token;
    }
    console.warn('  X token refresh failed:', r.error || res.status);
  }

  return stored?.access_token || envToken || null;
}

// ── Platforms ─────────────────────────────────────────────────────────────────

const DISCORD_MAX_BYTES  = 20 * 1024 * 1024; // free-tier cap as of Aug 2026; boosted servers allow more
const TELEGRAM_MAX_BYTES = 50 * 1024 * 1024; // standard cloud Bot API cap

async function postDiscord(url, message, videoPath) {
  const token   = process.env.DISCORD_BOT_TOKEN;
  const channel = process.env.DISCORD_CHANNEL_ID;
  if (!token || !channel) return { platform: 'Discord', skipped: true };

  if (videoPath && fs.statSync(videoPath).size <= DISCORD_MAX_BYTES) {
    const res = await postMultipart(
      `https://discord.com/api/v10/channels/${channel}/messages`,
      { headers: { Authorization: `Bot ${token}` } },
      [
        { name: 'payload_json', value: JSON.stringify({ content: message }) },
        { name: 'files[0]', filename: 'video.mp4', contentType: 'video/mp4', data: fs.readFileSync(videoPath) },
      ],
    );
    if (res.status === 200) return { platform: 'Discord', status: res.status, ok: true, attachedVideo: true };
    console.warn('  Discord video attach failed, falling back to link:', res.status, res.body.slice(0, 200));
  }

  const res = await post(
    `https://discord.com/api/v10/channels/${channel}/messages`,
    { headers: { Authorization: `Bot ${token}` } },
    { content: message },
  );
  return { platform: 'Discord', status: res.status, ok: res.status === 200 };
}

async function postTelegram(url, message, videoPath) {
  const token  = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) return { platform: 'Telegram', skipped: true };

  if (videoPath && fs.statSync(videoPath).size <= TELEGRAM_MAX_BYTES) {
    const res = await postMultipart(
      `https://api.telegram.org/bot${token}/sendVideo`,
      {},
      [
        { name: 'chat_id', value: chatId },
        { name: 'caption', value: message },
        { name: 'video', filename: 'video.mp4', contentType: 'video/mp4', data: fs.readFileSync(videoPath) },
      ],
    );
    const body = JSON.parse(res.body);
    if (body.ok) return { platform: 'Telegram', status: res.status, ok: true, attachedVideo: true };
    console.warn('  Telegram video attach failed, falling back to link:', res.status, res.body.slice(0, 200));
  }

  const res = await post(
    `https://api.telegram.org/bot${token}/sendMessage`,
    {},
    { chat_id: chatId, text: message },
  );
  const body = JSON.parse(res.body);
  return { platform: 'Telegram', status: res.status, ok: body.ok };
}

async function postX(url, message) {
  const token = await getXToken();
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
      'LinkedIn-Version': process.env.LINKEDIN_API_VERSION || '202607',
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
  if (res.status !== 200 && res.status !== 201) {
    return { platform: 'Moltbook', status: res.status, ok: false };
  }
  const body = JSON.parse(res.body);
  const post_ = body.post || {};
  // A 200/201 here does NOT mean the post is live - Moltbook requires
  // solving a math-puzzle verification challenge (POST /verify with
  // post.verification.verification_code) within 5 minutes, or the post
  // stays permanently "pending" and invisible in feeds/search. Confirmed
  // the hard way: an earlier automated post reported success here and
  // sat unverified until its window expired. This function doesn't
  // attempt to solve the challenge (it's deliberately obfuscated,
  // inconsistent between addition/multiplication, and not reliably
  // regex-parseable) - it just reports honestly instead of lying.
  if (post_.verification_status === 'pending') {
    console.warn(`  Moltbook: post ${post_.id} created but NOT yet visible - needs manual verification within 5 min. Challenge: ${post_.verification?.challenge_text}`);
    return { platform: 'Moltbook', status: res.status, ok: false, needsVerification: true, postId: post_.id, verificationCode: post_.verification?.verification_code, challengeText: post_.verification?.challenge_text };
  }
  return { platform: 'Moltbook', status: res.status, ok: true };
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function run() {
  const message = CUSTOM || `New video: ${YT_URL}`;
  const xMessage = process.env.X_MESSAGE || message;

  console.log(`Announcing to social platforms...`);
  console.log(`Message: ${message.slice(0, 80)}${message.length > 80 ? '...' : ''}\n`);
  if (xMessage !== message) {
    console.log(`X message override: ${xMessage.slice(0, 80)}${xMessage.length > 80 ? '...' : ''}\n`);
  }
  if (VIDEO_PATH) {
    console.log(`Video: ${VIDEO_PATH} (${(fs.statSync(VIDEO_PATH).size / 1_000_000).toFixed(1)} MB) - attaching natively where supported\n`);
  }

  const results = await Promise.allSettled([
    postDiscord(YT_URL, message, VIDEO_PATH),
    postTelegram(YT_URL, message, VIDEO_PATH),
    postX(YT_URL, xMessage),
    postMoltbook(YT_URL, message),
    postLinkedIn(YT_URL, message),
  ]);

  for (const r of results) {
    if (r.status === 'fulfilled') {
      const { platform, skipped, ok, status, attachedVideo } = r.value;
      if (skipped) {
        console.log(`  ${platform}: skipped (no credentials configured)`);
      } else if (ok) {
        console.log(`  ${platform}: posted ✓${attachedVideo ? ' (video attached)' : ''}`);
      } else {
        console.log(`  ${platform}: FAILED (HTTP ${status})`);
      }
    } else {
      console.log(`  ERROR: ${r.reason?.message || r.reason}`);
    }
  }
}

run().catch(err => { console.error('Error:', err.message || err); process.exit(1); });
