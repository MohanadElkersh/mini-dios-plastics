# Mini-DIOS Plastics — User Guide & Operations Manual

> **What this document is:** A plain-language guide explaining what **Mini-DIOS Plastics** does, why it protects factory profit, and how to use every screen step by step.
> **Who it is for:** Factory owners, operations directors, production planners, shift supervisors, and finance leaders running injection molding, blow molding, or extrusion plants in Egypt and Saudi Arabia.
> **What it helps you do:** Turn your weekly list of presses, molds, resins, customer orders, and floor staff into a conflict-free production schedule, shift roster, and weekly profit plan in seconds.

---

## 1. Why Mini-DIOS Plastics Exists

Most plastics factories still plan their weekly production on spreadsheets or whiteboards, scheduling jobs simply by whichever order is due first. That feels logical on paper, yet it quietly drains profit every week through six everyday factory-floor realities:

1. **Costly Dark-to-Light Color Purges:** Moving a press from a light color (like Natural or White) to a darker color (like Blue, Red, or Black) takes a quick flush—about **25 minutes and 4 kg** of resin. Going backward from a dark color to a light color requires a deep barrel cleanout—roughly **2 hours 15 minutes and 32 kg** of virgin resin thrown away as purge scrap. Switching between incompatible plastics (such as moving between polyolefins like PP/HDPE/LDPE and PET, ABS, or PVC) wastes even more—around **3 hours and 48 kg**.
2. **Avoidable Mold Changeovers:** Hanging and stabilizing a different physical mold takes **80 to 155 minutes** of press downtime, creates **4 to 10 kg** of startup scrap, and keeps barrel heaters burning electricity while making zero sellable parts.
3. **Press and Mold Mismatches:** Assigning a hot-runner mold to a cold-runner press—or accidentally scheduling the same physical mold on two presses at once—causes floor delays and emergency reshuffling.
4. **Surprise Mold Maintenance Stops:** Running a mold past its safe shot-count limit risks expensive cavity damage and multi-day unscheduled downtime.
5. **Resin Pre-Drying Delays:** Moisture-sensitive resins like **PET** and **ABS** must be dried for hours (typically **6 hours**) before molding starts. Forgetting drying time leads to rejected batches and missed shipments.
6. **Peak Electricity Bills & Unmatched Shift Overtime:** Running heavy 500T–650T presses blindly through peak afternoon electricity hours (**13:00–17:00**, when power costs **40% more**) and keeping a rigid 6-day staff rotation regardless of how many presses or mold changes are actually running inflates both utility and payroll bills.

### Why Exact Mathematical Scheduling Beats Spreadsheets and Generic AI
- **Compared to spreadsheets:** Instead of sorting orders only by due date, Mini-DIOS tests thousands of combinations in seconds to group compatible molds, run colors cleanly from light to dark, protect export deadlines, and match floor technicians to actual changeover peaks.
- **Compared to generic AI chatbots:** Chatbots guess words—they cannot reliably solve factory schedules and often make arithmetic mistakes. In Mini-DIOS, **100% of schedules, shift rosters, and profit numbers are calculated by exact mathematical rules**—never guesswork—and you need **zero years of historical data** to start on Day 1.
- **Clear Cause-and-Effect Decision Rules:** Every floor policy (from light-to-dark color purging and food-grade zero-regrind rules to mold maintenance thresholds and shift staffing ratios) is organized into clear, auditable business rule tables, and every management priority slider traces directly through intermediate shop-floor metrics (purge scrap, changeover hours, container waiting time, and overtime hours) straight to weekly net operating profit.
- **Built for total privacy:** Your factory can run Mini-DIOS privately on its own local server (even with zero internet connection), keeping customer names, selling prices, and production volumes strictly inside your building.

---

## 2. Getting Started & Global Controls

When you open Mini-DIOS Plastics (either in your private hosted sandbox or on your factory server), you will see a clean top bar with controls that apply across all six tabs:

- **Peak Tariff Avoid (`ON` / `OFF`):** Tells the scheduler to steer energy-heavy runs away from expensive afternoon peak electricity hours (default **13:00–17:00**) and shades those hours on the schedule timeline.
- **Ramadan Shift (`ON` / `OFF`):** Automatically applies Ramadan operating rules—pauses mold changeovers during the daily **18:00–20:00** Iftar window, switches floor staffing to **four 6-hour shifts** per day, caps weekly hours at **36 hours** (30 standard hours), and adjusts shift labor costs accordingly.
- **Auto PM (`ON` / `OFF`):** Lets the scheduler automatically choose the cheapest, least disruptive time window during the week to perform required mold preventive maintenance (PM) before a mold hits its shot-count limit, instead of forcing maintenance at the very start of the week.
- **Container & WIP Sync (`ON` / `OFF`):** Coordinates multi-item export shipments that share a shipping container so one product does not finish days early and sit on the warehouse floor trapping working capital while waiting for the rest of the container.
- **Currency Switch (`SAR` / `EGP`):** Converts every cost, selling price, wage, and profit figure instantly between Saudi Riyals and Egyptian Pounds using your configured exchange rate (default **13.0 EGP per SAR**).
- **Language Switch (`العربية` / `English`):** Flips the entire workspace between English and full right-to-left Arabic in one click.
- **Ops Copilot:** Opens the side-panel assistant where you can ask plain-English or Arabic *"what if?"* questions.
- **Run Optimization:** Recalculates your press schedule, floor shift roster, financial report, and risk alerts in a few seconds.
- **Admin Live Engine Switcher (For Authorized Demo Administrators):** When signed in as an administrator, clicking the **`Admin`** button in the top-right corner opens a control panel to switch live between the classic scheduling engine and the **5-Layer Decision Intelligence Engine** (which coordinates machine schedules and available shift staff in both directions) and download the plant's formal process and business rule blueprints—affecting only the administrator's current demo session without interrupting any other user.
- **Executive Brief (Dual-Audience Switcher, Printable PDF & WhatsApp Dispatch):** Opens a clean, one-screen boardroom summary with a two-tab audience switcher at the top:
  - **Owner / Chairman View:** Focuses on turning veteran floor know-how into permanent **Institutional Memory**, ending daily friction between Production, Warehouse, and Finance, and showing **Annualized Cash & Working Capital Unlocked** plus **1-Month Historical Backtest ROI**.
  - **Plant / Production Manager View:** Frames the schedule as a **Decision Shield**—giving the Plant Manager instant mathematical proof to justify overtime, relief staffing, protected mold maintenance windows, and the true cost of mid-week rush orders.
  - **Download / Print Executive PDF & WhatsApp Shift Dispatch:** From inside the Executive Brief (or the 1-Month Historical Backtest window), click **`Download / Print Executive PDF`** to preview and print a clean, ink-friendly 1–2 page executive report in English or Arabic. Or click **`WhatsApp Shift Dispatch`** to copy or share a formatted daily shift run list and crew roster directly over WhatsApp.

Directly beneath the top bar is the **5-Step Decision Strip** (`1. Model → 2. Sense → 3. Optimize → 4. Command → 5. Adapt`). Clicking any step jumps straight to the matching screen.

---

## 3. Tab-by-Tab Walkthrough

Out of the box, Mini-DIOS comes loaded with a realistic example factory (**Delta & Riyadh Polymer Packaging Plant**: 6 presses, 10 molds, 5 resin grades, 24 weekly orders, and 28 floor workers) so you can explore every screen immediately.

### Tab 1 — Plant Scope & Readiness
Your daily starting screen for checking factory health before building a schedule:
- **Saved Plant Workspaces, Decision Checkpoints & Guided 5-Step Plant Setup:** Switch between different plants or saved versions, click **`Decision Checkpoints`** to open your persistent decision history and roll back to any earlier plant state (such as before a rush order or Copilot simulation) in one click, or click **`Guided 5-Step Plant Setup`** to launch a plain-language 5-step interview (covering your molding process, press fleet & backup crossover rules, light-to-dark color batching & regrind allowance, shift pattern & peak electricity avoidance, and export container & warehouse storage rules). At Step 5 of the Guided Setup, a **"Current Specs Only" 3-Hour Onboarding Checklist** confirms that you only need today's active mold cavities, part weights, press power ratings, and morning silo stock—**never messy historical sales or accounting tables**.
- **Instant Quick-Add Hub, Capable-to-Promise (CTP) Rush-Order Quoter & 1-Month Historical Backtest:** Quickly add a new press, mold, resin, or order, adjust factory rules, or use two powerful decision tools right from Tab 1:
  - **Quote Rush Order (CTP):** Lets owners and sales directors test an urgent customer inquiry (*"Can we take this 40,000-piece rush order, when will it finish, what is our true break-even unit price, and whose order gets delayed?"*) **without altering the live schedule**. Click **`Load Sample Rush Order (40k Export)`** for a 10-second live demonstration. The quoter shows a color-coded verdict (`Green: Ships On Time`, `Amber: Ships Late / Cut-Off Impact`, `Red: Exceeds Capacity / Resin Deficit`), itemized marginal costs (direct resin, extra color purge scrap, extra mold changeover, extra power, and extra shift overtime), the **Minimum Break-Even Unit Price**, and the exact list of **Bumped Confirmed Orders**. You can then either click **`Discard Quote`** (leaving your active schedule untouched) or **`Accept & Add to Live Schedule`** (which commits the order, saves a Decision Checkpoint, and updates the entire dashboard).
  - **1-Month Historical Backtest (The Proof Engine):** Download a simple log template, upload 2–4 weeks of your factory's actual past press logs (or click **`Run Sample 30-Day Plant Replay`**), and view an apples-to-apples **Actual Factory History vs. Mini-DIOS Replay Card** with a 1-click **`Download / Print Executive PDF`** button.
- **6 Clickable Summary Cards:** Shows active presses, molds (highlighting any that need maintenance), resin grades, weekly orders (and how many are exports), overall plant load, and active vs. sick floor staff. Click any card to jump straight to that list.
- **Proactive Risk Radar (Including Warehouse & Trapped Container Alerts):** Gives your week an early-warning **Plant Risk Score (0–100)**, total financial exposure, export orders at risk, tightest delivery buffer, **Warehouse Congestion & Trapped Export Container Alerts** (when early batching fills finished-goods storage or leaves partial export containers waiting for sibling items), and a **Resin Silo Depletion Clock** showing when any resin is projected to run low. Every warning card has a **`Mitigate in Copilot`** button that simulates an actionable floor fix—such as synchronizing multi-item export containers, adding relief staff for bottleneck roles to close understaffed shifts, pulling export runs earlier to widen port cut-off buffers, topping up a low resin silo, or logging completed mold maintenance—and lets you apply it across the entire dashboard in one click.
- **Resin Inventory vs. Weekly Demand:** Visual bars compare how much resin this week's orders need against your available virgin and usable regrind stock, flagging drying times (such as 6 hours for PET and ABS). Click the edit icon on any resin to update stock or prices on the spot.
- **Mold Shot-Count Maintenance Health:** Shows how close each mold is to its rated maintenance shot limit (any mold at **95% or higher** is flagged for mandatory maintenance—like Mold `M-04` in the sample plant). Once your toolroom completes maintenance, click **`PM`** to reset that mold's shot counter back to zero.
- **Pre-Solve Diagnostics:** Confirms your plant data is ready (`READY`) or highlights any blocking mistake (such as an order linked to a press that is currently marked down) before you run the schedule.

### Tab 2 — Plant Data & Parameters
Your complete factory editor, organized into five sub-tabs:
- **A. Presses:** Manage every injection, blow-molding, or extrusion machine—tonnage, whether it supports hot-runner molds, electricity draw per hour, hourly operating cost, active/down status, and planned maintenance windows.
- **B. Molds:** Manage physical molds—which presses can mount them, cavity count, cycle time in seconds, hot-runner vs. cold-runner type, physical changeover time, current shot count, maintenance interval, and PM duration.
- **C. Resin Inventory & Pricing:** Set available virgin and regrind stock (in kg), cost per kg, pre-drying lead time (hours), and barrel temperature for each plastic grade (`PP`, `HDPE`, `LDPE`, `PET`, `ABS`, `PVC`).
- **D. Production Orders:** Search, filter, add, or edit weekly customer orders—customer name, product, mold, resin, plastic color (`Natural`, `White`, `Yellow`, `Blue`, `Red`, `Black`), quantity, part weight, maximum allowed regrind percentage (**0% for food and pharma orders—strictly protected**), due hour, hourly late penalty, export priority flag, and **Unit Selling Price**.
- **E. Plant Physics & Solver Rules:** Fine-tune your factory's real-world numbers—light-to-dark and dark-to-light purge minutes and kg, incompatible resin purge rates, electricity tariff, peak surcharge window, inventory holding cost, currency and exchange rate, planning horizon (default 168 hours = 1 week), Ramadan shift hours, weekly fixed overhead, scrap regrind recovery credit, and annual operating weeks (default 50).

Click **`Validate & Run Optimization →`** at the top right whenever you want to jump straight to the Press Gantt, or simply make your edits—Mini-DIOS automatically keeps your production schedule, shift roster, financial report, 5-Step Decision Strip, and Risk Radar synchronized in lockstep whenever you change plant data, priority sliders, top-bar switches, or worker availability.

### Tab 3 — Trade-Off & Scenario Composer
Built for leadership decisions and crisis rehearsals:
- **4 Top Savings Cards:** Immediately compares your optimized plan against a traditional due-date (**FIFO — First-In, First-Out**) schedule, showing **Total Cash Saved**, **Purge Resin Scrap Cut (kg)**, **Changeover Hours Saved**, and **On-Time In-Full Delivery (`OTIF %`)**.
- **4 Executive Priority Sliders:** Adjust what matters most this week—**Purge & Changeover**, **Export OTIF** (protecting customer and port deadlines), **Energy Cost**, and **Working Capital**—or pick one of four instant presets (`Balanced Plant`, `Min Purge Scrap`, `Zero Late Exports`, `Min Electricity`).
- **Custom Scenario Composer:** Combine as many real-world disruptions at once as you want:
  - **Press Breakdown:** Take any press offline at any hour for any duration.
  - **Resin Shock:** Cut available virgin stock by a percentage, simulate a virgin price spike, or raise the **Non-Food Regrind Cap** (up to 40% for industrial orders while keeping food/pharma orders strictly at 0%).
  - **Rush Order:** Drop in an urgent export or domestic order mid-week.
  - **Mold PM Lock:** Lock any mold out for immediate preventive maintenance.
- **Pin & Compare (A vs. B vs. C):** Click **`Pin Scenario`** to freeze your current plan as **Plan A (Anchor)**, then run a disruption or alternative strategy and pin it as **Plan B** (or **Plan C**). The **Scenario Comparison Matrix** places all pinned plans side by side with exact profit, scrap, delivery, overtime, and risk differences, marks the best option automatically, and lets you promote your preferred plan with one click.
- **Export-Container Consolidation & Finished-Goods Warehouse Sync:** Displays live **Peak Warehouse Utilization %**, **Trapped Container Working Capital**, **WIP Staging (Ton-Days)**, and **Max Container Staging Spread (hrs)** across your multi-item export shipments, with a one-click **`Container & WIP Sync`** switch to align container completion times.
- **Rule Verification & History:** Confirms **100% compliance** with every press, mold, resin, and maintenance rule, and lets you reload any previous run from the audit history.

### Tab 4 — Press Gantt & Color Sequence
The visual 7-day (`Sun–Sat`) floor schedule for every press:
- **Optimized vs. Traditional FIFO Toggle:** Switch back and forth between the optimized schedule and the traditional due-date schedule (both buttons show total purge scrap kg) to see how chaotic dark-to-light purges turn into smooth **Light → Dark** sequences (`Natural → White → Yellow → Blue → Red → Black`) with batched molds.
- **Easy Visual Reading:** Production blocks match the actual plastic color. Hatched amber blocks mark changeovers and purges; hatched red blocks mark breakdowns or maintenance; hatched purple blocks mark mold PM windows. When enabled, vertical shaded bands show Peak Electricity hours and Ramadan Iftar blackouts.
- **Zoom & Hover Details:** Toggle **`Fit Horizon`** vs. **`Detailed Zoom`** and hover over any job to inspect start/end times, mold, resin, changeover duration, and purge scrap.
- **Resin & Sequence Audit + One-Click Schedule Export & WhatsApp Shift Dispatch:** Below the timeline, side-by-side charts compare purge scrap by resin, and a full execution table lists every job in exact press order alongside **`Export Schedule`** buttons (**`Excel (.xlsx)`**, **`Flat CSV (.csv)`**, **`ERP JSON`** for Odoo or SAP Business One, and **`WhatsApp Shift Dispatch`** for sending clean press run sequences, purge alerts, and assigned shift crew to floor supervisors in English or Arabic).

### Tab 5 — Revenue & Savings
Your CFO-ready weekly financial statement:
- **1-Month Historical Backtest & Container Working Capital Strip:** Launch the **`1-Month Historical Backtest (Proof Engine)`** directly from the top of Tab 5, and inspect the live **Trapped Container Working Capital**, **Finished-Goods Warehouse Peak Load**, **WIP Holding Volume (Ton-Days)**, and **Weekly WIP & Container Holding Cost** strip right above the financial cards.
- **5 Executive Financial Cards:**
  1. **Weekly Recognized Revenue** (highlighting any revenue at risk if a resin shortage blocks an order)
  2. **Optimized Net Profit & Margin %** (with margin lift over traditional FIFO)
  3. **Total Weekly Savings** (the combined benefit of lower costs and protected revenue)
  4. **Annualized Projected Savings** (weekly savings scaled across your operating weeks per year, plus monthly projection)
  5. **Unlocked Capacity Value** (the revenue value of press hours freed by cutting changeovers)
- **Inline Financial Assumptions:** Adjust Weekly Fixed Overhead, Scrap Regrind Recovery %, or Annual Operating Weeks directly on the page and watch every figure update automatically.
- **Side-by-Side Weekly Profit & Loss (P&L):** Reconciles **Recognized Revenue** minus every itemized cost—**Direct Resin**, **Net Purge Scrap**, **Energy & Press Operating**, **Late Delivery Penalties**, **Inventory Holding**, **Direct Floor Labor & Overtime** (synced live from Tab 6), and **Weekly Fixed Overhead**—straight down to **Net Operating Profit** with zero double-counting.
- **Per-Order Profitability Table:** Search any customer or product and edit its **Unit Selling Price** right in the table to see its true margin immediately.

### Tab 6 — Workforce & Shifts
Automatically matches your floor crew to your solved Press Gantt:
- **Automatic Press-to-People Coupling:** For every shift of the week, Mini-DIOS calculates exact staffing needs directly from Tab 4's press schedule:
  - **Press Operators:** Scales with active presses (default 1 operator per 2 presses) and checks that each operator is certified for the running machines.
  - **Shift Supervisors:** 1 per active operating shift.
  - **QC Inspectors & Material Handlers:** 1 per active shift, adding an extra person during heavy press load (4+ presses) or when running moisture-sensitive PET/ABS resins.
  - **Mold Technicians:** Automatically scheduled whenever mold changeovers or PM blocks occur (2 technicians during heavy changeover peaks).
- **5 Workforce KPI Cards:** Active vs. sick headcount, **Weekly Labor & Overtime Saved** (versus a static 6-day rotation), **Overtime Hours Reduced**, **Shift & Changeover Coverage %**, and **100% Rest-Rule & Labor-Law Compliance**.
- **Live Controls & Sick-Callout Rehearsal:** Adjust the balance between Labor Cost, Shift Coverage, and Fairness; set minimum rest hours between shifts (default 11 hours) and consecutive days off; tap any technician or operator to mark them sick, then click **`Re-Optimize Shifts`** to rebuild the roster and update Tab 5's labor cost line instantly.
- **Roster Matrix, Coverage Chart, Worker Directory & Export Buttons:** View every worker's 7-day schedule (`Morning`, `Afternoon`, `Evening` during Ramadan, `Night`, `OFF`, `LEAVE`, `SICK`), spot any understaffed shift on the coverage chart, add or edit worker leave days and machine certifications directly in the directory, and export the complete schedule and shift roster to **Excel**, **CSV**, or **ERP JSON** in one click.

---

## 4. Using the Operations Copilot (English & Arabic)

Click **`Ops Copilot`** in the top bar (or click **`Mitigate in Copilot`** on any Tab 1 Risk Radar alert) to ask plain-language *"what if?"* questions in English or Arabic.

Examples you can type—or click as starter chips:
- *"Press 500T breaks down for 18 hours on Tuesday."*
- *"HDPE supply is cut by 35%—boost non-food regrind to cover it."*
- *"Add an urgent 40,000-piece White Cap export order due Thursday."*
- *"Compare Lowest Purge Scrap vs. Zero Late Exports."*
- *"Why is Mold M-04 a bottleneck?"*
- *"What happens to shift coverage and profit if 2 Mold Technicians and 3 Press Operators call out sick on Tuesday?"*

Every answer is calculated by the exact same deterministic scheduling engine—never guessed by an AI chatbot. At the top of every simulation card, a highlighted **Commander-Grade Financial Trade-Off Analysis** box summarizes the exact **Cost Paid** versus **Value Protected** and the **Net Financial Gain** in `EGP` or `SAR` (for example, showing how a small increase in power or shift overtime protects tens of thousands in export penalties and purge resin waste). From any Copilot response, you can click **`Pin for Comparison`** to add it to your side-by-side comparison matrix, or **`Apply This Scenario to Dashboard`** to push the complete updated factory state (including any added relief workers, replenished resin stock, updated priority sliders, press schedule, shift roster, weekly profit & loss, and recalculated Risk Radar) live across all six tabs. As soon as you apply a scenario, a **Before → After Applied Summary Banner** appears at the top of the dashboard and inside Copilot showing how your **Plant Risk Score**, **Exports at Risk**, **Shift Coverage %**, and **Understaffed Slots** changed—and clearly explaining if any physical floor limit (such as available headcount or virgin resin stock) still requires attention.

---

## 5. Common Questions & Quick Fixes

- **Why is the "Run Optimization" button disabled?** Tab 1 or Tab 2 detected a blocking data error (for example, an order assigned to a press that is marked down). Check the red diagnostic banner in Tab 1 or Tab 2 to see which item needs fixing.
- **Why does an order appear as "Unscheduled (Resin Cap)"?** Your total virgin resin needed for production and purging exceeds the virgin stock on hand for that grade. Either increase your virgin inventory in Tab 1/Tab 2, or enable the **Non-Food Regrind Cap** in Tab 3 to free virgin resin for food and export orders.
- **Why does Mold M-04 have a purple maintenance block at the start of the week?** In the sample plant, `M-04` is at **96.4%** of its rated shot life (above the 95% safety limit). Turn **`Auto PM`** ON in the top bar to let the scheduler place that maintenance in the cheapest available gap, or click **`PM`** in Tab 1 once maintenance is completed.
- **Can a planner accidentally allow recycled regrind in a food or pharma order?** No. Any order set to **0% maximum regrind** is strictly protected—even if you activate a plant-wide regrind boost during a resin shortage.
- **Does Mini-DIOS still work if our factory has no internet connection?** Yes. All scheduling, shift rostering, financial math, risk alerts, and Copilot simulations run 100% locally inside your factory server with zero internet required.

---

*For developers and IT teams: see the separate Technical Reference document.*
