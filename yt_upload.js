#!/usr/bin/env node
/**
 * yt_upload.js  —  e3d-pod2vid
 *
 * Uploads a video to YouTube using the resumable upload API.
 * Handles large files reliably with automatic token refresh.
 *
 * Usage:
 *   node yt_upload.js <video.mp4> "<title>" [description]
 *
 * Environment variables:
 *   YT_CLIENT_SECRET   path to youtube-client-secret.json (default: youtube-client-secret.json)
 *   YT_TOKEN_FILE      path to token file (default: youtube-tokens.json)
 *   YT_PRIVACY         unlisted | public | private (default: public)
 *   YT_CATEGORY        YouTube category ID (default: 28 = Science & Technology)
 *   YT_TAGS            comma-separated tags (default: AI,podcast,autonomous vehicles)
 */

'use strict';
require('dotenv').config();

const fs    = require('fs');
const https = require('https');
const path  = require('path');
const { URLSearchParams } = require('url');

const SECRET_FILE = process.env.YT_CLIENT_SECRET || 'youtube-client-secret.json';
const TOKEN_FILE  = process.env.YT_TOKEN_FILE    || 'youtube-tokens.json';
const PRIVACY     = process.env.YT_PRIVACY       || 'public';
const CATEGORY    = process.env.YT_CATEGORY      || '28';
const TAGS        = (process.env.YT_TAGS || 'AI,podcast,autonomous vehicles').split(',');

const VIDEO_PATH = process.argv[2];
const TITLE      = process.argv[3] || path.basename(VIDEO_PATH || '', '.mp4');
const DESCRIPTION= process.argv[4] || '';

function httpsReq(url, opts, body) {
  return new Promise((resolve, reject) => {
    const parsed = require('url').parse(url);
    const req = https.request(Object.assign(parsed, opts), res => {
      let data = '';
      res.on('data', d => (data += d));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
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
  const res = await httpsReq('https://oauth2.googleapis.com/token',
    { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded',
                                  'Content-Length': Buffer.byteLength(body) } }, body);
  const r = JSON.parse(res.body);
  if (r.error) throw new Error(`Token refresh failed: ${r.error_description || r.error}`);
  Object.assign(tokens, r);
  tokens.expiry_date = Date.now() + (r.expires_in || 3600) * 1000;
  fs.writeFileSync(TOKEN_FILE, JSON.stringify(tokens, null, 2));
  return tokens;
}

async function initResumable(accessToken, metadata, fileSize) {
  const body = JSON.stringify(metadata);
  const res  = await httpsReq(
    `https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status`,
    { method: 'POST', headers: {
        'Authorization':  `Bearer ${accessToken}`,
        'Content-Type':   'application/json; charset=UTF-8',
        'Content-Length': Buffer.byteLength(body),
        'X-Upload-Content-Type': 'video/mp4',
        'X-Upload-Content-Length': fileSize,
    }}, body,
  );
  if (res.status !== 200 && res.status !== 200) {
    if (!res.headers.location) throw new Error(`Init failed ${res.status}: ${res.body}`);
  }
  return res.headers.location;
}

async function uploadChunks(uploadUrl, filePath, fileSize) {
  const CHUNK = 8 * 1024 * 1024; // 8 MB
  const fd    = fs.openSync(filePath, 'r');
  let offset  = 0;
  let videoId = null;

  try {
    while (offset < fileSize) {
      const end    = Math.min(offset + CHUNK, fileSize);
      const length = end - offset;
      const buf    = Buffer.alloc(length);
      fs.readSync(fd, buf, 0, length, offset);

      const parsed = require('url').parse(uploadUrl);
      const res = await new Promise((resolve, reject) => {
        const req = https.request(Object.assign(parsed, {
          method: 'PUT',
          headers: {
            'Content-Length': length,
            'Content-Range':  `bytes ${offset}-${end - 1}/${fileSize}`,
          },
        }), res => {
          let data = '';
          res.on('data', d => (data += d));
          res.on('end', () => resolve({ status: res.statusCode, body: data }));
        });
        req.on('error', reject);
        req.write(buf);
        req.end();
      });

      if (res.status === 308) {
        offset = end;
        const pct = Math.round((offset / fileSize) * 100);
        process.stdout.write(`\r  Uploading... ${pct}%`);
      } else if (res.status === 200 || res.status === 201) {
        const r = JSON.parse(res.body);
        videoId = r.id;
        process.stdout.write('\n');
        break;
      } else {
        throw new Error(`Upload chunk error ${res.status}: ${res.body.slice(0, 200)}`);
      }
    }
  } finally {
    fs.closeSync(fd);
  }
  return videoId;
}

async function run() {
  if (!VIDEO_PATH || !fs.existsSync(VIDEO_PATH)) {
    console.error(`Usage: node yt_upload.js <video.mp4> "<title>" [description]`);
    process.exit(1);
  }
  for (const f of [SECRET_FILE, TOKEN_FILE]) {
    if (!fs.existsSync(f)) {
      console.error(`Missing: ${f}. Run "node yt_auth.js" first.`);
      process.exit(1);
    }
  }

  const rawCreds = JSON.parse(fs.readFileSync(SECRET_FILE));
  const creds    = rawCreds.installed || rawCreds.web;
  let tokens     = JSON.parse(fs.readFileSync(TOKEN_FILE));
  tokens         = await refreshToken(tokens, creds);

  const fileSize = fs.statSync(VIDEO_PATH).size;
  console.log(`Uploading: ${VIDEO_PATH}  (${(fileSize / 1_000_000).toFixed(1)} MB)`);
  console.log(`Title: ${TITLE}`);

  const metadata = {
    snippet: {
      title: TITLE, description: DESCRIPTION,
      tags: TAGS, categoryId: CATEGORY,
    },
    status: { privacyStatus: PRIVACY },
  };

  const uploadUrl = await initResumable(tokens.access_token, metadata, fileSize);
  if (!uploadUrl) throw new Error('No upload URL returned from YouTube');
  console.log('Upload session initiated.');

  const videoId = await uploadChunks(uploadUrl, VIDEO_PATH, fileSize);
  if (!videoId) throw new Error('Upload completed but no video ID returned');

  const url = `https://www.youtube.com/watch?v=${videoId}`;
  console.log(`\nUploaded: ${url}`);
  console.log(`Video ID: ${videoId}`);
  console.log(`\nTo update description/thumbnail: node yt_update.js ${videoId}`);
  console.log(`To announce: node announce.js ${url}`);
}

run().catch(err => { console.error('\nError:', err.message || err); process.exit(1); });
