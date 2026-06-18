# TimeWinder Operations Hub — Home Assistant integration

A custom [Home Assistant](https://www.home-assistant.io/) integration for the
**TimeWinder Operations Hub** (drift). It signs in with the Hub's SMS one-time-password
flow, polls the read-only operational endpoints, and exposes them as sensors you can put
on dashboards and build automations on.

## Sensors

| Entity | Source | Notes |
| ------ | ------ | ----- |
| `sensor.timewinder_operations_hub_open_total` | `/api/command-center` `open.total` | Attributes: `unassigned`, `critical`, `high`, `blocked` |
| `sensor.timewinder_operations_hub_new_in_window` | `command-center` `newInWindow` | New incidents in the window |
| `sensor.timewinder_operations_hub_open_followups` | `command-center` `escalations.openFollowUps` | Attribute `items` = open follow-ups |
| `sensor.timewinder_operations_hub_sms_failed` | `command-center` `sms.failed` | Failed SMS in the window |
| `sensor.timewinder_operations_hub_users_online` | `/api/analytics/live` `users` | Users online now |
| `sensor.timewinder_operations_hub_incidents` | `/api/incidents?filter=team` | State = count, attribute `items` = up to 25 incidents |
| `sensor.timewinder_operations_hub_need_help` | `command-center` `availabilityByTeam` | Sum of NeedHelp across teams; attribute `teams` = per-team availability counts/members |
| `sensor.timewinder_operations_hub_team_load` | `command-center` `teamLoad` | Number of teams; attribute `teams` = open/unassigned/criticalHigh per team |
| `sensor.timewinder_operations_hub_top_points` | `command-center` `topPoints` | Count; attribute `points` = busiest reporting points |
| `sensor.timewinder_operations_hub_response_ack` | `command-center` `responseTimes` | Avg minutes to first engagement (duration); attributes include resolve time + per-priority |
| `sensor.timewinder_operations_hub_sessions` | `/api/analytics/overview` | Total sessions in the window; attributes `users`, `pageViews`, `events`, `series`, `days` |
| `sensor.timewinder_operations_hub_delivery` | `/api/delivery-overview` | Row count; attribute `rows` = delivered vs sold per bar/product (Varegaard/Sekretariat) |
| `sensor.timewinder_operations_hub_bar_orders` | `/api/bar-orders` | Open order count; attribute `items` = orders (fulfiller role) |

Entity ids are stable and locale-independent (`sensor.timewinder_operations_hub_<key>`), set explicitly by the integration since v0.2.2.

> The command-center and analytics sensors require the signed-in account to have the
> **Drift Coordinator** role. Without it those endpoints return 403 and the sensors stay
> empty — but `sensor.timewinder_operations_hub_incidents` (team-scoped) still works for team leads.

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
