/**
 * PM2 config for scheduled e3d signal → video pipeline.
 *
 * Start:   pm2 start ecosystem.config.js --env production
 * Stop:    pm2 delete signal-short
 * Logs:    pm2 logs signal-short
 */
module.exports = {
  apps: [
    {
      name:        'signal-short',
      script:      'python3',
      args:        'signal_short.py',
      cwd:         __dirname,
      cron_restart:'0 14 * * *',   // 14:00 UTC daily (10am ET)
      autorestart: false,
      watch:       false,
      env_production: {
        NODE_ENV:            'production',
        // Copy from .env or set here:
        OPENAI_API_KEY:      process.env.OPENAI_API_KEY      || '',
        PEXELS_API_KEY:      process.env.PEXELS_API_KEY      || '',
        MAPS_URL:            process.env.MAPS_URL             || 'https://maps.e3d.ai',
        MAPS_INTERNAL_KEY:   process.env.MAPS_INTERNAL_KEY   || '',
        CONF_THRESHOLD:      process.env.CONF_THRESHOLD       || '0.78',
        DISCORD_BOT_TOKEN:   process.env.DISCORD_BOT_TOKEN   || '',
        DISCORD_CHANNEL_ID:  process.env.DISCORD_CHANNEL_ID  || '',
        TELEGRAM_BOT_TOKEN:  process.env.TELEGRAM_BOT_TOKEN  || '',
        TELEGRAM_CHAT_ID:    process.env.TELEGRAM_CHAT_ID    || '',
        X_CLIENT_ID:         process.env.X_CLIENT_ID         || '',
        X_CLIENT_SECRET:     process.env.X_CLIENT_SECRET     || '',
        X_TOKEN_FILE:        process.env.X_TOKEN_FILE        || '',
        MOLTBOOK_API_KEY:    process.env.MOLTBOOK_API_KEY    || '',
        MOLTBOOK_API_URL:    process.env.MOLTBOOK_API_URL    || 'https://www.moltbook.com/api/v1',
        LINKEDIN_TOKEN_FILE: process.env.LINKEDIN_TOKEN_FILE || 'linkedin-tokens.json',
        YT_CLIENT_SECRET:    process.env.YT_CLIENT_SECRET    || 'youtube-client-secret.json',
        YT_TOKEN_FILE:       process.env.YT_TOKEN_FILE       || 'youtube-tokens.json',
      },
    },
  ],
};
