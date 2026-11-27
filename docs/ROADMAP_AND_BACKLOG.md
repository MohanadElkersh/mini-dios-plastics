# Mini-DIOS Plastics — Product Roadmap & Future Factory Constraints Backlog

> **What this document is:** A plain-language roadmap of future factory floor rules and scheduling options that we keep ready on the shelf, organized by when and why to add them during a factory pilot.
> **Who it is for:** Founders, sales directors, implementation engineers, and factory partners planning a 60-day pilot or a multi-site rollout in Egypt and Saudi Arabia.
> **What it helps you do:** Keep the core scheduling system fast, simple, and easy to adopt on Day 1—while knowing exactly which specialized factory rules can be turned on whenever a specific customer asks for them.

---

## 1. Our "Pilot-Pull Only" Product Philosophy

Every plastics factory has unique habits on the shop floor. However, stuffing fifty extra settings into a scheduling screen on Day 1 overwhelms planners and slows down onboarding.

Instead, **Mini-DIOS Plastics** follows a strict **Pilot-Pull Rule**:
- **Day 1 Core (Already Live Today):** Focuses on the rules that drive 85% of weekly cash savings in injection and blow-molding plants—press and mold compatibility, light-to-dark color purge sequencing, mold preventive maintenance shot limits, resin pre-drying and inventory caps, multi-item export container synchronization, finished-goods warehouse capacity, peak electricity avoidance, Ramadan 6-hour shifts, capable-to-promise (CTP) rush-order quoting, decision checkpoints, and 1-click executive PDF and WhatsApp shift dispatch.
- **Pilot-Pull Extensions (Logged Below):** Parked cleanly on our roadmap and switched on **only when a factory owner or production manager explicitly asks for that rule** during a live pilot.

---

## 2. Future Factory Constraints Backlog (Pilot-Pull Only)

### Tier 1 — High-Likelihood Pilot Requests (Add Only When a Factory Asks)

These six floor realities come up frequently in mid-to-large Egyptian and Saudi packaging plants. Each one is pre-designed so our team can activate it quickly during a paid pilot whenever a factory needs it:

1. **Shared Auxiliary Equipment (Cranes, Chillers, Dryers & Robots):**
   - *Overhead Crane Contention:* Heavy molds (on 500T–650T presses) require the bay's single overhead bridge crane. If two heavy presses schedule a mold swap at the exact same minute, one crew has to wait. This rule limits simultaneous heavy mold changeovers to match the number of cranes in the hall.
   - *Summer Chiller Tonnage Caps:* During 45°C summer afternoons in Riyadh, Jeddah, or Upper Egypt, central chilled-water capacity can become a bottleneck when too many fast-cycling thin-wall molds run together. This rule caps total cooling demand across running molds at any hour.
   - *Shared Portable Dryers & Take-Out Robots:* Prevents scheduling more simultaneous runs requiring portable dehumidifying dryers or side-entry robots than the floor physically owns.
2. **Capped / Blocked Mold Cavities:**
   - In real toolrooms, a 16-cavity cap or preform mold often runs with 1 or 2 damaged cavities plugged (for example, 14 active cavities out of 16 nominal cavities) until the next major overhaul.
   - This rule lets the planner enter the active cavity count so run duration and resin draw adjust automatically without creating a fake mold record.
3. **Multi-Stage Production Dependencies (Preform-to-Blow & Cap-to-Bottle Matching):**
   - *Two-Stage PET Molding:* A blow-molding line cannot blow 1-liter bottles until the injection press has molded and cooled the matching PET preforms.
   - *Matched Component Sets:* A customer order for 100,000 jerrycans and 100,000 tamper-evident caps cannot pack or ship until both the container mold and the cap mold finish their paired batches.
4. **Order Splitting & Duplicate / Parallel Molds:**
   - High-volume beverage cap or dairy tub plants sometimes own two identical molds (`Mold A` and `Mold B`) or want to split a 500,000-piece export run across two presses—or into staggered weekly call-off deliveries—to meet an urgent vessel cut-off.
5. **Mid-Week Inbound Supply & Packaging Stockouts:**
   - Instead of checking only Monday morning resin silo stock, this rule tracks mid-week resin truck arrivals (for example, a 25-ton SABIC HDPE delivery arriving Wednesday at 10:00) alongside color masterbatch, printed cartons, IML labels, and wooden export pallets.
6. **Secondary / Downstream Bottlenecks (Printing, Labeling & Assembly):**
   - Many dairy tubs, cosmetic jars, and industrial pails require post-molding decoration—offset dry-offset printing, In-Mold Labeling (IML) robot setup, pad printing, or ultrasonic welding. This rule prevents presses from flooding the printing room faster than the downstream finishing machines can clear the work.

---

### Tier 2 — Sub-Sector & Heavy-Plant Phase 2

These specialized rules apply to heavy industrial, automotive, medical, or continuous extrusion factories and are reserved for Phase 2 enterprise engagements:

- **Hard Plant Electrical Transformer Ceilings (kVA Peak-Demand Caps):** Industrial zones in 10th of Ramadan, 6th of October, Borg El Arab, and Saudi MODON cities penalize plants or trip main breakers if simultaneous machine startup and heating loads exceed the transformer's rated kVA ceiling.
- **Insert-Only Swaps vs. Full Mold Changes (Family Molds & Neck-Ring Cores):** Swapping a date stamp, logo insert, or bottle neck-ring inside a mold frame while the base stays bolted in the press takes 25–35 minutes instead of a full 2-hour crane changeover.
- **Thermal Barrel Heat-Up & Cool-Down Soak Windows:** Switching a barrel from a high-temperature engineering plastic (like PET, Polycarbonate, or Nylon at 275°C–300°C) down to standard Polypropylene or Polyethylene (200°C) requires a controlled thermal cool-down window so residual plastic does not burn or carbonize on the screw.
- **Quality Control Quarantine & First-Article Lab Hold Buffers:** Food-contact, pharmaceutical, and automotive orders often require a mandatory 2-hour first-article lab inspection before full-speed running—or a 12-to-24-hour cooling, shrinkage, and leak-test quarantine before finished cartons can be loaded into an export container.
- **Extrusion-Specific Physics (Pipe, Film, Sheet & Jumbo-Roll Slitting):** Continuous extrusion lines run by die-width and wall-thickness campaigns rather than discrete mold cavities, require periodic screen-pack filter swaps as back-pressure builds, and need width-slitting optimization when cutting master film jumbo rolls into customer roll widths.

---

### Tier 3 — Explicit Pilot Scope Traps (Defer Post-Pilot)

To protect fast 3-hour setup and guaranteed Week-1 ROI, we explicitly decline or defer the following three requests during an initial pilot:

1. **Live Machine Sensor & PLC Wiring (IoT Polling):** Wiring hardware boxes into legacy Chinese, European, or Taiwanese press controllers takes months of electrical maintenance permits and IT security approvals. A morning Excel/CSV upload or a 2-minute supervisor checkpoint update delivers 95% of the scheduling value with zero hardware delay.
2. **3D Pallet & Warehouse Rack Bin-Packing:** Tracking exact forklift aisle and shelf slots belongs in a Warehouse Management System (WMS). Tracking total finished-goods tonnage and export container waiting times inside Mini-DIOS is all a scheduler needs to prevent warehouse overflow.
3. **Last-Mile Delivery Fleet GPS Routing:** Routing delivery trucks through Cairo or Riyadh traffic belongs in a Transport Management System (TMS). For production scheduling, ex-works factory gate readiness and port container cut-off hours are the right boundary.

---

*For developers and IT teams: see the separate Technical Reference document for the parked mathematical design notes.*
