# Scent Smart — Home Assistant custom integration

BLE control for the **Scent GAS-501F aroma diffuser** (Scent/YooAI).
Protocol validated end-to-end on 2026-11-02 (ACK + state dump + official app).

## Installation

**Via HACS (custom repo):** copy this directory into a git repo as
`custom_components/scent_smart/`, add the repo in HACS → Integrations → ⋮ →
Custom repositories (category *Integration*), then install "Scent Smart".

**Manual:** copy the `scent_smart/` folder to `/config/custom_components/scent_smart/`
and restart Home Assistant.

Then: Settings → Devices & Services → Add Integration → **Scent Smart**.
Enter the device's BLE address (e.g. `54:6C:50:5E:C3:6F`, advertisement name
starts with `Scent-`) and a friendly name. Options allow default run/pause
times, window start/stop, active program and the spray-now duration.

> Requirements: bleak>=0.21.0 (bundled with HA's bluetooth integration image).
> The device supports **only one central at a time** — close the official app
> before using HA.

## Entities

| Entity | Platform | Function |
|---|---|---|
| `switch.scent_smart_working_mode` | switch | Running status (CMD 0x07, func 0x12) |
| `switch.scent_smart_fan` | switch | Fan toggle (0x10) |
| `switch.scent_smart_child_lock` | switch | Child lock toggle (0x11) |
| `light.scent_smart_ambient_light` | light | Ambient light 0=off / 1=on (0x15) |
| `button.scent_smart_spray_now` | button | One-shot spray; restores previous run time afterwards |
| `number.scent_smart_spray_duration` | number | Run time of ACTIVE program (5–200 s, step 5) |
| `number.scent_smart_pause_time` | number | Suspend time of ACTIVE program (20–300 s, step 5) |
| `select.scent_smart_active_program` | select | program_1 … program_5 |
| `switch.scent_smart_program_1..5_enabled` | switch | Enable flag per program (CMD 0x14) |
| `sensor.scent_smart_state` | sensor | Running/Idle/Off + `run_time`, `pause_time`, `window_start`, `window_stop`, `raw_dump`, `unknown_fields` |

## Automation examples

### Presence-based working mode (off when nobody home)

```yaml
automation:
  - alias: Scent diffuser presence
    triggers:
      - trigger: state
        entity_id: binary_sensor.home_occupied
    actions:
      - action: switch.turn_{{ 'on' if trigger.to_state.state == 'on' else 'off' }}
        target: { entity_id: switch.scent_smart_working_mode }
```

### Spray once when the front door opens

```yaml
automation:
  - alias: Scent on door open
    triggers:
      - trigger: state
        entity_id: binary_sensor.front_door
        to: "on"
    actions:
      - action: button.press
        target: { entity_id: button.scent_smart_spray_now }
```

### Schedule quiet nights (turn working mode off at 22:00)

```yaml
automation:
  - alias: Scent night off
    triggers:
      - trigger: time
        at: "22:00:00"
    actions:
      - action: switch.turn_off
        target: { entity_id: switch.scent_smart_working_mode }
```

## Protocol notes

- Single characteristic FFE1 (service FFE0), write **without response**; state
  arrives via NOTIFY (reads are READ_NOT_PERMITTED).
- Frame `55 AA | LEN | CMD | payload | CK | 5A`; CK = `256 - sum(0x55..payload) % 256` (0 if 0); u16/u32 LE.
- CMD 0x14 = 16-byte timer `[enable, serial, mode u16, start u16, stop u16, run u16, suspend u16, tail 01 00 00 00]`.
- CMD 0x07 func 0x01 **starts the factory default cycle** (60 s/200 s) — it is never used as a query.
- The 0x21 state-dump layout beyond the validated timer block and ACK frames is
  unknown; unparsed bytes are surfaced in the sensor's `unknown_fields`
  attribute as raw hex instead of being guessed.
