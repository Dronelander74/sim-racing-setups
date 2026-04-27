# PMR Tyre Pressure Policy
> Versione: 1.0 | Uso: PMRRuleEngine.js — logica pressioni gomme

---

## 1. Unità

Tutte le pressioni nel vset PMR sono in **Pascal (Pa)**.
Display UI in **bar** (divide per 100000).

Esempi:
- `156000 Pa` = `1.56 bar`
- `178000 Pa` = `1.78 bar`

---

## 2. Pressioni Baseline per Classe Auto (a freddo, asciutto, 25°C aria / 30°C pista)

Le pressioni di partenza riflettono il carico aerodinamico e il peso tipico della classe.

| Classe | Front (Pa) | Rear (Pa) | Note |
|---|---|---|---|
| `MX-5` / `SPEC` | 152000 | 148000 | Auto leggera, poco carico |
| `GT4` | 162000 | 158000 | |
| `GT3` | 172000 | 168000 | |
| `GT500` | 178000 | 174000 | |
| `Group C` | 182000 | 178000 | Alto carico aerodinamico |
| `LMDh` | 186000 | 182000 | Massimo carico, auto pesante |
| `964_TROPHY` / `CHALLY` | 158000 | 154000 | Fallback generico |

---

## 3. Delta Temperatura Pista

La temperatura pista influenza quanto la gomma scalda durante il giro.
Pista più calda → gomma scalda di più → pressione a freddo più bassa.

```
delta_temp = -(trackTempC - 30) * 150  [Pa per °C]
```

Esempi:
- `trackTempC = 50°C` → `delta = -(50-30)*150 = -3000 Pa`
- `trackTempC = 15°C` → `delta = -(15-30)*150 = +2250 Pa`

---

## 4. Delta Temperatura Aria

Temperatura aria fredda → pressioni a freddo più alte per compensare.

```
delta_air = -(ambientTempC - 20) * 80  [Pa per °C]
```

Esempi:
- `ambientTempC = 35°C` → `delta = -(35-20)*80 = -1200 Pa`
- `ambientTempC = 5°C`  → `delta = -(5-20)*80  = +1200 Pa`

---

## 5. Delta Meteo (Pioggia)

| Condizione | rainLevel | Delta Pressione |
|---|---|---|
| Dry | 0 | 0 Pa |
| Light Rain | 1 | -4000 Pa |
| Medium Rain | 2 | -6000 Pa |
| Heavy Rain | 3 | -8000 Pa |

Formula: `delta_rain = -rainLevel * (8000/3) Pa`

---

## 6. Delta Caratteristiche Pista

| Tag pista | Delta Front | Delta Rear | Motivo |
|---|---|---|---|
| `high_speed` | +1500 Pa | +1000 Pa | Stabilità aerodinamica ad alta velocità |
| `tyre_wear` > 0.65 | -1500 Pa | -1500 Pa | Riduce surriscaldamento su piste logoranti |
| `bumpy` | -1000 Pa | -1000 Pa | Più flessibilità su sconnessioni |

---

## 7. Formula Finale

```
pressure_front = baseline_front[carClass]
              + delta_temp
              + delta_air
              + delta_rain
              + delta_track_front

pressure_rear  = baseline_rear[carClass]
              + delta_temp
              + delta_air
              + delta_rain
              + delta_track_rear
```

Il valore finale deve essere clampato a `[120000, 220000] Pa` (1.20 – 2.20 bar) come guardrail assoluto.

---

## 8. Mapping Classe Auto → Categoria Pressione

Il campo `carClass` del `PmrCarCatalog` deve essere mappato alla categoria pressione:

| carClass in DB | Categoria pressione |
|---|---|
| `GT3` | `GT3` |
| `GT4` | `GT4` |
| `GT500` | `GT500` |
| `LMDh` | `LMDh` |
| `Group C` | `Group C` |
| `MX-5_SPEC` / `MX-5_TROPHY` / `MX-5_PLUS` | `MX-5` |
| `964_TROPHY` | `964_TROPHY` |
| `CHALLY` | `CHALLY` |

Il `PMRRuleEngine` riceve `carClass` nel contesto e lo usa per selezionare il baseline corretto.

---

## 9. Note Implementazione

- Il file di policy viene letto da `PMRRuleEngine.js` nella funzione `computeTyrePressures(carClass, trackProfile, weather)`
- I valori baseline sono hardcoded in questo file — per modificarli basta aggiornare la tabella §2
- Non serve aggiornare i car range pack — le pressioni non sono constraint di pack ma valori calcolati dalla policy
- Il vset PMR usa `FL-tire-pressure`, `FR-tire-pressure`, `RL-tire-pressure`, `RR-tire-pressure` in Pa
