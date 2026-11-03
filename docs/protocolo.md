# Protocolo BLE — Difusor GAS-501F (app com.yooai.scentlife v47)

Fonte: decompilação androguard do XAPK (classes2.dex). Canal único: FFE1 (svc FFE0).

## Frame (getBytes — BleUtils)
```
55 AA | LEN | CMD | payload | CK | 5A
LEN   = len(payload) + 1
CK    = 256 - (soma dos bytes de 0x55 até payload % 256); 0 se mod == 0
```
Encrypted variant (só p/ modelos com senha BLE): payload = XOR com chave
`ba08a5e898094021b71960278a97cf35`, + 1 byte final = índice inicial do XOR.
GAS-501F sem senha → payload em claro.

## Comandos (CMD byte)
| CMD | Payload | Significado |
|-----|---------|-------------|
| 0x06 | u32 LE unixtime | syncTime (relógio do aparelho) |
| 0x07 | [func, valor, 0x00] | operation — toggle de estado |
| 0x07 | [func, val_lo, val_hi] | numeric — setar parâmetro u16 LE |
| 0x09 | [sub, len, dados] | F() — genérico (uso interno) |
| 0x14 | 16 bytes TimerVo | **timer/período** (rz::P) |
| 0x15 | 25 bytes DeviceType | capacidades (x7::e — info, não comando) |
| 0x17 | multi-pump: [idx, func, nvals, vals...] | só aparelhos multi-bomba |
| 0x46 | wifi ssid/pwd | provisioning WiFi (outros modelos) |
| 0x48/0x4B | [len, senha] | senha BLE |
| 0x4C | [len_lo, len_hi, nome] | rename |

## Funcs do 0x07 (operation)
| func | Ação | valor |
|------|------|-------|
| **0x12** | **Running status** (liga/desliga ciclo autônomo) | 0/1 |
| 0x10 | Fan | 0/1 (toggle) |
| 0x11 | Device lock (child lock) | 0/1 (toggle) |
| 0x15 | Ambient light | 0=off, 1=on, 2=modo |
| 0x14 | resetLevel | [0x14, canal, nível] |
| 0x01 | **START ciclo padrão** (cria/retoma working mode de fábrica: 60s run / 200s suspend — confirmado ao vivo) | 0 |
| 0x08/0x09/0x03/0x57 | variantes Grasse (outro modelo) | — |

## Funcs numéricos (0x07 u16 LE)
| func | Significado | Faixa |
|------|-------------|-------|
| 0x31 | Capacidade da garrafa (ml) | 1–5000 |
| 0x32 | Consumo (×10; 0–3267.7) | 1–32767 |
| 0x33 | Óleo disponível (ml) | 1–capacidade |

## TimerVo (CMD 0x14) — payload 16 bytes
```
[0]    enable        u8   0/1
[1]    serialNum     u8   0..4  ← OS 5 GRUPOS DE PERÍODO
[2:4]  mode          u16 LE
[4:6]  start         u16 LE  (minuto do dia; old-agreement usava h*60+m)
[6:8]  stop          u16 LE
[8:10] run           u16 LE  ← SPRAY (segundos) — u16, sem teto de 8!
[10:12] suspend      u16 LE  ← PAUSA (segundos) — u16, sem teto de 10min!
[12:16] timerId      u32 LE
```
Display no app: "Run time: %ds | Stop time: %ds".

## Notas
- DeviceVo.isSwitch() = o flag mostrado como "Running status" no app.
- O aparelho responde estado via NOTIFY no FFE1 (read é READ_NOT_PERMITTED).
- Frame de estado tem parsed 3 != 0xD1: [4]=1 → dados em offset 5..; [4]=2 → offset 13..
- a.a(func,val) faz: write + postDelayed(sync 0x01/0x00, 5000ms) — sempre re-sync após comando.
