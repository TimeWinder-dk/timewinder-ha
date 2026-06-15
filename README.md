# TimeWinder Operations Hub — Home Assistant integration

A custom [Home Assistant](https://www.home-assistant.io/) integration for the
**TimeWinder Operations Hub** (drift). It signs in with the Hub's SMS one-time-password
flow, polls the read-only operational endpoints, and exposes them as sensors you can put
on dashboards and build automations on.

## Sensors

| Entity | Source | Notes |
| ------ | ------ | ----- |
| `sensor.*_abne_sager` | `/api/command-center` `open.total` | Attributes: `unassigned`, `critical`, `high`, `blocked` |
| `sensor.*_nye_sager` | `command-center` `newInWindow` | New incidents in the window |
| `sensor.*_abne_eskaleringer` | `command-center` `escalations.openFollowUps` | Attribute `items` = open follow-ups |
| `sensor.*_sms_fejlet` | `command-center` `sms.failed` | Failed SMS in the window |
| `sensor.*_brugere_online` | `/api/analytics/live` `users` | Users online now |
| `sensor.*_sagsliste` | `/api/incidents?filter=team` | State = count, attribute `items` = up to 25 incidents |

> The command-center and analytics sensors require the signed-in account to have the
> **Drift Coordinator** role. Without it those endpoints return 403 and the sensors stay
> empty — but `sensor.*_sagsliste` (team-scoped) still works for team leads.

## Authentication

The Hub issues a **30-day token** via SMS OTP — there is no silent refresh. The config flow:

1. You enter the **API URL** (default `https://tw-opshub-func.azurewebsites.net` — the Azure Functions host, **not** the `drift.timewinder.dk` SPA) and your **CrewNet email**.
2. The Hub sends a 6-digit code by SMS.
3. You enter the code → a 30-day token is stored in the config entry.

When the token expires, Home Assistant raises a **reauth** notification: open it, a new code
is sent, type it in, done. No YAML, no secrets in files.

## Install via HACS

1. HACS → ⋮ → **Custom repositories**.
2. Repository: `https://github.com/TimeWinder-dk/timewinder-ha`, type **Integration**.
3. Install **TimeWinder Operations Hub**, then restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → TimeWinder Operations Hub** and follow the SMS login.

## Manual install

Copy `custom_components/timewinder_ops` into your HA `config/custom_components/` directory and restart.

## Example dashboard card

```yaml
type: entities
title: TimeWinder Drift
entities:
  - sensor.timewinder_abne_sager
  - sensor.timewinder_abne_eskaleringer
  - sensor.timewinder_sms_fejlet
  - sensor.timewinder_brugere_online
```

## License

MIT
