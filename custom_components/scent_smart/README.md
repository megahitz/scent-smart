# Scent Smart

A local BLE integration for Home Assistant, tested with a GAS-501F diffuser.

See the [project documentation](https://github.com/megahitz/scent-smart) for installation, entities, tests, and limitations. A [Portuguese version](https://github.com/megahitz/scent-smart/blob/main/README.pt-BR.md) is also available.

The integration connects on demand; after Home Assistant restarts, states may remain unknown until an action receives a valid response.

Spray Now requires a known working mode and program 1 to be enabled. The complete spray flow with the mode off has not been validated on the device, and a failure can prevent restoration of the previous state.
