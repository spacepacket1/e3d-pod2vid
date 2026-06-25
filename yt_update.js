#!/usr/bin/env node
/**
 * yt_update.js  —  e3d-pod2vid
 *
 * Updates a YouTube video's description and thumbnail after upload.
 *
 * Usage:
 *   node yt_update.js <videoId> [thumbnail.png]
 *
 * Environment variables:
 *   YT_CLIENT_SECRET   path to client secret JSON (default: youtube-client-secret.json)
 *   YT_TOKEN_FILE      path to token file (default: youtube-tokens.json)
 *   YT_DESCRIPTION     full description text (can be multiline via $'...' in shell)
 */

'use strict';
require('dotenv').config();

const fs    = require('fs');
const https = require('https');
const path  = require('path');
const { URLSearchParams } = require('url');

const SECRET_FILE = process.env.YT_CLIENT_SECRET || 'youtube-client-secret.json';
const TOKEN_FILE  = process.env.YT_TOKEN_FILE    || 'youtube-tokens.json';

const VIDEO_ID  = process.argv[2];
const THUMB     = process.argv[3] || '';

const DESCRIPTION = process.env.YT_DESCRIPTION || '';

function httpsJson(url, opts, body) {
  return new Promise((resolve, reject) => {
    const parsed = require('url').parse(url);
    const req = https.request(Object.assign(parsed, opts), res => {
      let data = '';
      res.on('data', d => (data += d));
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

async function refreshToken(tokens, creds) {
  if (tokens.expiry_date && tokens.expiry_date > Date.now() + 60_000) return tokens;
  console.log('Refreshing access token...');
  const body = new URLSearchParams({
    client_id: creds.client_id, client_secret: creds.client_secret,
    refresh_token: tokens.refresh_token, grant_type: 'refresh_token',
  }).toString();
  const res = await httpsJson('https://oauth2.googleapis.com/token',
    { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded',
                                  'Content-Length': Buffer.byteLength(body) } }, body);
  if (res.body.error) throw new Error(`Token refresh: ${res.body.error_description}`);
  Object.assign(tokens, res.body);
  tokens.expiry_date = Date.now() + (res.body.expires_in || 3600) * 1000;
  fs.writeFileSync(TOKEN_FILE, JSON.stringify(tokens, null, 2));
  return tokens;
}

async function getSnippet(videoId, token) {
  const url = `https://www.googleapis.com/youtube/v3/videos?part=snippet&id=${videoId}`;
  const res = await httpsJson(url, {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${token}` },
  });
  const items = res.body.items || [];
  if (!items.length) throw new Error(`Video ${videoId} not found`);
  return items[0].snippet;
}

async function updateDescription(videoId, snippet, description, token) {
  const body = JSON.stringify({
    id: videoId,
    snippet: { ...snippet, description },
  });
  const res = await httpsJson(
    `https://www.googleapis.com/youtube/v3/videos?part=snippet`,
    { method: 'PUT', headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
    }}, body,
  );
  if (res.status !== 200) throw new Error(`Update failed ${res.status}: ${JSON.stringify(res.body)}`);
  console.log('Description updated.');
}

async function uploadThumbnail(videoId, thumbPath, token) {
  const data    = fs.readFileSync(thumbPath);
  const boundary = 'e3dpod2vid_boundary';
  const header  = Buffer.from(
    `--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{}\r\n` +
    `--${boundary}\r\nContent-Type: image/png\r\n\r\n`,
  );
  const footer  = Buffer.from(`\r\n--${boundary}--`);
  const payload = Buffer.concat([header, data, footer]);

  return new Promise((resolve, reject) => {
    const url   = `https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=${videoId}&uploadType=multipart`;
    const parsed = require('url').parse(url);
    const req = https.request(Object.assign(parsed, {
      method: 'POST',
      headers: {
        'Authorization':  `Bearer ${token}`,
        'Content-Type':   `multipart/form-data; boundary=${boundary}`,
        'Content-Length': payload.length,
      },
    }), res => {
      let body = '';
      res.on('data', d => (body += d));
      res.on('end', () => {
        if (res.statusCode !== 200) return reject(new Error(`Thumbnail ${res.statusCode}: ${body.slice(0,200)}`));
        console.log('Thumbnail uploaded.');
        resolve();
      });
    });
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

async function run() {
  if (!VIDEO_ID) {
    console.error('Usage: node yt_update.js <videoId> [thumbnail.png]');
    process.exit(1);
  }

  const rawCreds = JSON.parse(fs.readFileSync(SECRET_FILE));
  const creds    = rawCreds.installed || rawCreds.web;
  let tokens     = JSON.parse(fs.readFileSync(TOKEN_FILE));
  tokens         = await refreshToken(tokens, creds);
  const token    = tokens.access_token;

  console.log(`Video ID: ${VIDEO_ID}`);

  const snippet = await getSnippet(VIDEO_ID, token);
  console.log(`Current title: ${snippet.title}`);

  if (DESCRIPTION) {
    await updateDescription(VIDEO_ID, snippet, DESCRIPTION, token);
  } else {
    console.log('No YT_DESCRIPTION set — skipping description update.');
  }

  if (THUMB && fs.existsSync(THUMB)) {
    console.log(`Uploading thumbnail: ${THUMB}`);
    await uploadThumbnail(VIDEO_ID, THUMB, token);
  } else if (THUMB) {
    console.warn(`Thumbnail not found: ${THUMB}`);
  }

  console.log(`Done. https://www.youtube.com/watch?v=${VIDEO_ID}`);
}

run().catch(err => { console.error('Error:', err.message || err); process.exit(1); });
