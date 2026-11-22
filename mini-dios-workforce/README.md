# Mini-DIOS Plastics

**Decision Intelligence Operating System for Plastic Manufacturing Factories** (Injection Molding, Blow Molding & Extrusion — Egypt & Saudi Arabia).

- **100% Deterministic Google OR-Tools CP-SAT Engine** — `AddCircuit` sequence-dependent setup/color/resin purge + `AddNoOverlap` press & physical mold exclusivity.
- **6 Hard Constraints (Zero Violations):** Mold–Press compatibility & hot-runner fit, No press overlap & breakdown/downtime exclusion, Physical mold exclusivity across presses, Asymmetric changeover & light-to-dark color/resin purge sequencing, Resin pre-drying floor (PET/ABS 6h) & virgin/regrind inventory caps (food/pharma 0% regrind protection), and Mold Preventive Maintenance (PM) shot-count blocks.
- **Unlimited Composable Operations Copilot:** Gemini (`gemini-4-hydrogen`, `thinking_level="low"`, 15s `HttpOptions` timeout) with 3 deterministic CP-SAT tools (`simulate_plant_scenario`, `inspect_bottleneck`, `compare_two_strategies`) + zero-hang EN/AR offline parser. Zero LLM Math.
- **4-Tab Plastic Factory Excel Bridge:** Download `Presses`, `Molds`, `Resin_Inventory`, `Production_Orders` template, upload client `.xlsx` for anomaly validation, and export formatted executive briefs with color-coded Gantt schedules and purge scrap savings.
- **Bilingual EN (LTR) / Arabic (RTL) Executive Command Center** with EGP/SAR toggle, Peak Electricity Tariff Avoidance, Ramadan Shift Mode, Custom Composable Scenario Builder, Press-by-Press color-coded Gantt visualization, Executive Revenue & Savings P&L, and **Tab 6: Factory Workforce Management & Shift Scheduling** (coupled OR-Tools CP-SAT roster optimizer with 5 hard constraints, static-rotation baseline comparison, live P&L labor line, Copilot call-out simulation, and 100% in-dashboard worker CRUD).

## Quick Start (Local)

```bash
# Backend
cd backend
pytest -v
uvicorn main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm.cmd run build && npm.cmd run start
```
