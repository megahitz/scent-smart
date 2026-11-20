<p align="center"><img src="assets/icon.png" width="160" alt="Scent Smart"></p>

# Scent Smart

**English** | [Português (Brasil)](README.pt-BR.md)

A local Bluetooth integration for Home Assistant, tested with a **Scent-B501F (GAS-501F)** diffuser. Compatibility with other models has not been verified.

## Installation

**HACS:** under Integrations → Custom repositories, add `https://github.com/megahitz/scent-smart` as an integration. Install **Scent Smart** and restart Home Assistant.

**Manual:** copy `custom_components/scent_smart/` to `/config/custom_components/scent_smart/` and restart Home Assistant.

Then go to Settings → Devices & services → Add integration, select **Scent Smart**, and enter the device's Bluetooth address. Automatic discovery is not available in this version.

A nearby Bluetooth adapter or ESPHome proxy supporting active connections is required. The device may accept only one Bluetooth central connection at a time; close other Bluetooth clients before controlling it through Home Assistant.

## Entities

| Entity | Purpose |
|---|---|
| Working Mode | Turns the autonomous diffusion cycle on or off. |
| Spray Duration | Changes program 1: 5–200 seconds, in 5-second increments. |
| Pause Time | Changes program 1: 20–300 seconds, in 5-second increments. |
| Spray Now | Attempts to start a spray using the existing program 1. See the limitations below. |
| State | The last confirmed state response and diagnostic attributes. |

Other legacy controls for programs, fan, lock, lighting, and program selection are unavailable in this version. The device's existing schedule is preserved but cannot be edited here.

## Behavior and limitations

- The integration connects only for explicit actions; **there is no startup query or polling**. Connecting or sending a command may cause the device to beep.
- After Home Assistant restarts, the state and intervals may be **unknown** until an action returns valid data. Previously confirmed values can become stale if another control changes the device.
- Changing an interval queries the existing program, preserves its other fields, and verifies all five programs after writing. An acknowledgement alone is not treated as proof of a change.
- If a command times out or the connection fails after it is sent, the outcome is **unknown**: the device may have acted on it. Check before retrying.
- Spray Now requires a known working mode and program 1 to be enabled. When the mode is on, it reapplies the program; this action was tested on a GAS-501F. When the mode is off, it attempts to turn the mode on temporarily and back off after the configured time. This complete flow has not been validated on the device; a power interruption or connection failure can prevent restoration. Do not use it where the device remaining on would be a problem.
- The device retains its own schedule: removing a Home Assistant time restriction does not change that schedule. Continuous operation during the final minute of a schedule ending at 23:59 has not been established.

## Offline tests

From the repository root, run:

```bash
python3 -m unittest discover -s tests -v
```

The tests simulate Home Assistant and Bluetooth; they do not replace testing on the device. See the [validated protocol notes](docs/protocol.md).
