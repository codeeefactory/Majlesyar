# Telegram Bot

## Architecture

- Django app: `backend/telegram_bot`
- Transport:
  - Webhook view: `/api/v1/telegram/webhook/` by default
  - Polling runner: `python manage.py run_telegram_bot`
- Layers:
  - `services/client.py`: Telegram Bot API transport
  - `services/updates.py`: update dedupe and dispatch
  - `services/auth.py`: allowlist, chat checks, basic rate limiting
  - `services/handlers.py`: command and callback routing
  - `services/actions.py`: adapters over existing Majlesyar models and serializers
  - `services/notifications.py`: low-noise new-order notifications

## Security Model

- Disabled by default
- Requires explicit token and enable flag
- Deny-by-default allowlist for user IDs and optional chat IDs
- `ADMIN_ONLY` mode keeps the bot private
- Sensitive writes require explicit Telegram confirmation
- Every command and write creates an audit record
- Webhook requests can require `X-Telegram-Bot-Api-Secret-Token`
- Processed Telegram updates are deduplicated in DB
- Basic per-minute rate limiting is enforced from audit logs

## Supported Commands

- `/start`
- `/help`
- `/ping`
- `/whoami`
- `/status`
- `/health`
- `/dashboard`
- `/products [query]`
- `/product <slug-or-id>`
- `/feature <slug-or-id>`
- `/unfeature <slug-or-id>`
- `/activate <slug-or-id>`
- `/deactivate <slug-or-id>`
- `/orders [status]`
- `/order <public_id>`
- `/orderstatus <public_id> <status>`
- `/settings`

## Safe Management Scope

- Read:
  - Product lookup and search
  - Order lookup and recent order queues
  - Site settings snapshot
  - Dashboard summaries
- Write:
  - Toggle product `featured`
  - Toggle product `available`
  - Update order `status`
- Deferred:
  - Payment/refund operations
  - Deletes
  - Mass changes
  - User mutations
  - Support or moderation workflows not present in the current codebase

## Setup

1. Add environment variables.
2. Run migrations.
3. Start the bot with webhook or polling.
4. Open a chat with the bot from an allowed Telegram user.

## Webhook

Configure:

```powershell
python manage.py configure_telegram_webhook
```

Remove:

```powershell
python manage.py configure_telegram_webhook --delete
```

## Polling

```powershell
python manage.py run_telegram_bot
```

## Notifications

Send one-shot new-order notifications:

```powershell
python manage.py telegram_notify_new_orders
```

This command is safe to schedule via cron or systemd timer if needed.
