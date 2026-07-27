# Fluids

Pump sizing / piping head-loss calculations in US customary units (gpm, inches,
psi, ft), following Crane Technical Paper 410 (TP-410) conventions.

## Files

- **`fluids_english.py`** — the formula library. No project-specific numbers,
  just reusable functions (Reynolds number, friction factor, velocity head,
  brake horsepower, and resistance coefficients (K) for pipe runs, reducers,
  valves, fittings, and tees/wyes).
- **`heat_treat_unit_head_loss.py`** — a worked example: sizing a pump's
  discharge and suction head loss for a specific piping layout, using the
  library above.

## Units

Unless a function says otherwise:

| Quantity | Unit |
|---|---|
| Flow (Q) | gpm |
| Diameter / length | inches |
| Density (rho) | lb/ft3 |
| Viscosity (mu) | cP |
| Head | ft of fluid |
| Pressure | psi |

## Quick start

```python
from fluids_english import Re, f, K_L, h_L, v_ft_s, vel_head, P_from_H, bhp

Q, d, rho, mu, eta = 200, 2.067, 62.4, 1, 0.00015   # 200 gpm, 2" sch 40, water

reynolds = Re(Q, rho, d, mu)
friction = f(eta, d, reynolds)
K = K_L(friction, L=10, D=d)          # 10" of straight pipe
head_loss = h_L(K, Q, d)              # ft
psi_loss = P_from_H(rho, head_loss)
```

Call `list_functions()` at any time to print every public function in the
library with its signature and a one-line description:

```python
from fluids_english import list_functions
list_functions()
```

## What's in the library

- **Basic hydraulics**: `h_L`, `Re`, `v_ft_s`, `vel_head`, `P_from_H`, `bhp`,
  `discharge_Q` (flow from a known head, the inverse of `h_L`), `K_L`
  (straight-pipe friction K), `f` (Darcy friction factor via Colebrook,
  solved iteratively).
- **Reducers / contractions / enlargements**: `K_formula_1` through
  `K_formula_7` (Crane TP-410's formulas 1–7), plus `K_different_pipe_ID` for
  re-referencing a K value from one pipe diameter's velocity to another's.
- **Valves**: gate, globe (3 patterns), angle, ball, plug (3 types), swing
  check, lift check (2 patterns), stop check (6 types), tilting-disc check,
  butterfly, diaphragm (2 types), foot valve/strainer (2 types) — each
  optionally fitted with conical reducers.
- **Fittings**: smooth 90° bends (`K_90_bw`), bends at other angles
  (`K_elbow_angle`), mitre bends (`K_mitre`), threaded elbows/returns,
  pipe entrances/exits.
- **Tees and wyes**: converging and diverging branch/run formulas
  (`K_Tee_wye_converging`, `K_Tee_run`, `K_Tee_wye_diverging_branch`,
  `K_Tee_wye_diverging_run`).

Valve and Tee/Wye functions that reference table constants (`C`, `D`, `E`,
`F`, `G`, `H`, `J`, `M`, friction factors `f_t`) expect those values pulled
from the relevant Crane TP-410 table — **this library assumes you have a copy
of TP-410 on hand** for anything beyond the basic hydraulics formulas.

## Known gaps

- `K_formula_7` isn't dispatched to by any angle/beta check in the valve
  functions — confirm against TP-410 which range it actually covers before
  relying on it.
- The gate/ball valve helper (`_K_valve_reducer_by_angle`) has no covered
  case for `beta < 1` with `angle > 180°`; it returns `None` if you hit it.
