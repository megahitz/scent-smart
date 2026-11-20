# Protocol notes — GAS-501F

**English** | [Português (Brasil)](protocolo.md)

These notes apply to the tested device. They are not a specification for all BLE diffusers.

- Service `FFE0`, characteristic `FFE1`; messages are sent using write without response and received through notifications.
- Frame: `55 AA | LEN | CMD | payload | CK | 5A`. Length is the payload size plus one; the checksum is the additive complement of the bytes from the start through the end of the payload.
- Query `0x08` returned a `0x88` list of five programs on the tested device. An interval change uses the complete record and checks the list again after writing.
- Command `0x14` writes a program. Do not treat an ACK alone as confirmation of the values.
- Operation `0x12` controls working mode; the integration requires a matching state response before confirming the action.
- Operation `0x01` can replace the program with the default 60/200-second cycle. **Do not use it as a state query.**
- A general state query that does not change the mode has not been validated. Notification delivery conditions and behavior may differ on other models.

Before sending unknown commands, record the current configuration and assess the consequences. Failures and timeouts after a write do not prove that the device ignored the command.
