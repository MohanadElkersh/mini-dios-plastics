export type Currency = "EGP" | "SAR";
export type Lang = "en" | "ar";
export type ViewTab = "scope" | "studio" | "console" | "gantt" | "financials" | "workforce";
export type EngineMode = "uem_di_v1" | "legacy_cpsat_v1";
export type EngineOverrideInput = "uem_di_v1" | "legacy_cpsat_v1" | "default";
export type Severity = "error" | "warning" | "info";
export type ProcessType = "Injection" | "BlowMolding" | "Extrusion";
export type MachineStatus = "active" | "down" | "maintenance";
export type ResinCode = "PP" | "HDPE" | "LDPE" | "PET" | "ABS" | "PVC";
export type PlasticColor = "Natural" | "White" | "Yellow" | "Blue" | "Red" | "Black";

export type WorkerRole =
  | "Press_Operator"
  | "Mold_Technician"
  | "QC_Inspector"
  | "Material_Handler"
  | "Shift_Supervisor";
export type PreferredShift = "Morning" | "Afternoon" | "Night" | "Any";
export type WorkerStatus = "active" | "sick" | "on_leave";

export interface FactoryWorker {
  worker_id: string;
  name: string;
  role: WorkerRole;
  certified_machine_ids: string[] | "ALL";
  hourly_rate: number;
  overtime_multiplier: number;
  max_weekly_hours: number;
  preferred_shift: PreferredShift;
  approved_leave_days: number[];
  status: WorkerStatus;
}

export interface WorkforceConfig {
  shift_length_hrs: 6 | 8;
  standard_weekly_hours: number;
  min_rest_hours: number;
  min_consecutive_days_off: number;
  presses_per_operator: number;
  w_labor_cost: number;
  w_coverage: number;
  w_fairness: number;
}

export interface DowntimeWindow {
  start_hr: number;
  end_hr: number;
  reason: string;
}

export interface PressMachine {
  machine_id: string;
  name: string;
  process_type: ProcessType;
  tonnage: number;
  supports_hot_runner: boolean;
  hourly_energy_kwh: number;
  hourly_operating_cost: number;
  status: MachineStatus;
  downtime_windows: DowntimeWindow[];
}

export interface Mold {
  mold_id: string;
  name: string;
  compatible_machines: string[];
  cavities: number;
  cycle_time_sec: number;
  is_hot_runner: boolean;
  base_changeover_mins: number;
  current_shots: number;
  maintenance_interval_shots: number;
  pm_duration_hrs: number;
}

export interface ResinStock {
  resin_code: ResinCode;
  virgin_available_kg: number;
  virgin_cost_per_kg: number;
  regrind_available_kg: number;
  regrind_cost_per_kg: number;
  drying_lead_time_hrs: number;
  barrel_temp_c: number;
}

export interface ProductionOrder {
  order_id: string;
  customer: string;
  sku_name: string;
  mold_id: string;
  resin_code: ResinCode;
  color: PlasticColor;
  color_rank: number;
  quantity_pcs: number;
  part_weight_g: number;
  max_regrind_pct: number;
  due_hr: number;
  late_penalty_per_hr: number;
  is_export: boolean;
  container_group_id?: string | null;
  unit_selling_price: number;
  discount_pct: number;
}

export interface MachineBreakdown {
  machine_id: string;
  start_hr: number;
  duration_hrs: number;
}

export interface ResinShortage {
  resin_code: ResinCode;
  available_pct_reduction: number;
  virgin_price_spike_pct: number;
}

export interface MoldPmLock {
  mold_id: string;
  duration_hrs: number;
}

export interface ScenarioDisruptions {
  machine_breakdowns: MachineBreakdown[];
  resin_shortages: ResinShortage[];
  mold_pm_locks: MoldPmLock[];
  rush_orders: ProductionOrder[];
  allow_regrind_override_pct: number | null;
}

export interface PlantPhysicsConfig {
  horizon_hrs: number;
  light_to_dark_purge_mins: number;
  light_to_dark_purge_kg: number;
  dark_to_light_purge_mins: number;
  dark_to_light_purge_kg: number;
  incompatible_resin_purge_mins: number;
  incompatible_resin_purge_kg: number;
  energy_tariff_per_kwh: number;
  peak_tariff_multiplier: number;
  peak_start_hr: number;
  peak_end_hr: number;
  holding_cost_per_kg_per_day: number;
  ramadan_shift_hours: number;
  max_solve_seconds: number;
  weekly_fixed_overhead: number;
  scrap_regrind_recovery_pct: number;
  annual_operating_weeks: number;
  fg_storage_capacity_tons?: number;
  wip_holding_cost_per_ton_day?: number;
}

export interface SolverConfig {
  w_changeover_scrap: number;
  w_otif: number;
  w_energy_cost: number;
  w_working_capital: number;
  currency: Currency;
  fx_egp_per_sar: number;
  energy_tariff_per_kwh: number;
  avoid_peak_tariff_hrs: boolean;
  ramadan_shift_mode: boolean;
  autonomous_pm_window?: boolean;
  container_sync_enabled?: boolean;
  max_solve_seconds: number;
  random_seed: number;
  num_workers: number;
  physics: PlantPhysicsConfig;
  workforce: WorkforceConfig;
  scenarios: ScenarioDisruptions;
}

export interface PlantDataset {
  name: string;
  presses: PressMachine[];
  molds: Mold[];
  resins: ResinStock[];
  orders: ProductionOrder[];
  workers?: FactoryWorker[];
}

export interface Issue {
  code: string;
  severity: Severity;
  message: string;
  entity_type: string;
  entity_id?: string | null;
}

export interface ResinBalanceItem {
  resin_code: ResinCode;
  virgin_available_kg: number;
  regrind_available_kg: number;
  usable_regrind_kg: number;
  demand_kg: number;
  min_virgin_required_kg: number;
  drying_lead_time_hrs: number;
  barrel_temp_c: number;
  utilization_pct: number;
  deficit_kg: number;
}

export interface MoldHealthItem {
  mold_id: string;
  name: string;
  cavities: number;
  cycle_time_sec: number;
  is_hot_runner: boolean;
  current_shots: number;
  maintenance_interval_shots: number;
  shot_utilization_pct: number;
  pm_duration_hrs: number;
  needs_pm: boolean;
  active_compatible_presses: string[];
}

export interface ValidationReport {
  ready: boolean;
  error_count: number;
  warning_count: number;
  info_count: number;
  issues: Issue[];
  summary: {
    dataset_name: string;
    horizon_hrs?: number;
    presses_total: number;
    presses_active: number;
    molds_total: number;
    molds_needing_pm: number;
    resins_total: number;
    orders_total: number;
    export_orders: number;
    total_production_hrs: number;
    available_press_hrs: number;
    plant_load_pct: number;
    resin_balance: ResinBalanceItem[];
    mold_health: MoldHealthItem[];
    workers_total?: number;
    workers_active?: number;
    workers_sick?: number;
    workers_on_leave?: number;
  };
}

export interface ScheduledJob {
  order_id: string;
  customer: string;
  sku_name: string;
  machine_id: string;
  machine_name: string;
  mold_id: string;
  mold_name: string;
  resin_code: ResinCode;
  color: PlasticColor;
  color_rank: number;
  quantity_pcs: number;
  is_export: boolean;
  container_group_id?: string | null;
  gross_weight_kg?: number;
  container_wait_hrs?: number;
  scheduled: boolean;
  unscheduled_reason?: string | null;
  sequence_index: number;
  setup_start_min: number;
  start_min: number;
  end_min: number;
  duration_mins: number;
  setup_mins: number;
  purge_scrap_kg: number;
  transition_type: string;
  due_hr: number;
  tardiness_hrs: number;
  earliness_hrs: number;
  late_penalty_cost: number;
  virgin_kg: number;
  regrind_kg: number;
  resin_cost: number;
  purge_cost: number;
  energy_kwh: number;
  energy_cost: number;
  operating_cost: number;
  peak_overlap_mins: number;
}

export interface GanttBlock {
  block_id: string;
  machine_id: string;
  block_type: "production" | "changeover" | "breakdown" | "maintenance" | "mold_pm";
  label: string;
  start_min: number;
  end_min: number;
  order_id?: string | null;
  mold_id?: string | null;
  resin_code?: ResinCode | null;
  color?: PlasticColor | null;
  purge_scrap_kg: number;
  transition_type?: string | null;
  is_export: boolean;
  tardiness_hrs: number;
}

export interface ResinUsageSummary {
  resin_code: ResinCode;
  virgin_available_kg: number;
  regrind_available_kg: number;
  virgin_used_kg: number;
  regrind_used_kg: number;
  purge_scrap_kg: number;
  total_consumed_kg: number;
  remaining_virgin_kg: number;
  utilization_pct: number;
  virgin_cost_per_kg: number;
}

export interface PressSummary {
  machine_id: string;
  name: string;
  process_type: ProcessType;
  tonnage: number;
  status: MachineStatus;
  jobs_count: number;
  run_hrs: number;
  changeover_hrs: number;
  downtime_hrs: number;
  oee_pct: number;
  purge_scrap_kg: number;
  energy_kwh: number;
  energy_cost: number;
}

export interface KpiBlock {
  total_cost: number;
  resin_material_cost: number;
  purge_scrap_cost: number;
  energy_cost: number;
  operating_cost: number;
  late_penalty_cost: number;
  wip_holding_cost: number;
  changeover_hours: number;
  purge_scrap_kg: number;
  total_energy_kwh: number;
  peak_energy_hrs: number;
  total_run_hours: number;
  oee_pct: number;
  otif_pct: number;
  on_time_orders: number;
  late_orders: number;
  unscheduled_orders: number;
  total_orders: number;
  total_tardiness_hrs: number;
  virgin_resin_used_kg: number;
  regrind_resin_used_kg: number;
  weighted_objective: number;
  wip_holding_days?: number;
  peak_warehouse_tons?: number;
  fg_storage_capacity_tons?: number;
  warehouse_utilization_pct?: number;
  trapped_working_capital?: number;
  container_wait_delay_hrs?: number;
}

export interface ContainerGroupSummary {
  container_group_id: string;
  order_ids: string[];
  customers: string[];
  total_weight_tons: number;
  total_revenue_value: number;
  first_finish_hr: number;
  last_finish_hr: number;
  container_due_hr: number;
  spread_wait_hrs: number;
  wip_ton_days: number;
  trapped_working_capital: number;
  holding_cost: number;
  is_delayed: boolean;
}

export interface ScheduledMoldPm {
  mold_id: string;
  mold_name: string;
  machine_id: string;
  start_min: number;
  end_min: number;
  duration_hrs: number;
  mode: "autonomous" | "static_t0";
  trigger_reason: string;
  deadline_hr?: number | null;
}

export interface SchedulePlan {
  jobs: ScheduledJob[];
  gantt_blocks: GanttBlock[];
  resin_usage: ResinUsageSummary[];
  press_summaries: PressSummary[];
  unscheduled_order_ids: string[];
  mold_pm_windows?: ScheduledMoldPm[];
  container_groups?: ContainerGroupSummary[];
  kpis: KpiBlock;
}

export interface MetricCompare {
  baseline: number;
  optimized: number;
  delta: number;
  delta_pct: number;
}

export interface Scorecard {
  total_cost: MetricCompare;
  cash_savings: number;
  cash_savings_pct: number;
  purge_scrap_kg: MetricCompare;
  purge_scrap_kg_saved: number;
  purge_scrap_cost_saved: number;
  changeover_hours: MetricCompare;
  changeover_hours_saved: number;
  energy_and_late_savings: number;
  energy_cost: MetricCompare;
  late_penalty_cost: MetricCompare;
  oee_pct: MetricCompare;
  otif_pct: MetricCompare;
  weighted_objective: MetricCompare;
}

export interface ConstraintCheck {
  id: string;
  name: string;
  violations: number;
  passed: boolean;
  details: string[];
}

export interface AppliedScenario {
  type: string;
  description: string;
  affected_ids: string[];
}

export interface PlanFinancials {
  total_booked_revenue: number;
  recognized_revenue: number;
  at_risk_or_unscheduled_revenue: number;
  direct_resin_cost: number;
  purge_scrap_cost: number;
  purge_scrap_gross_cost: number;
  purge_scrap_recovery_credit: number;
  energy_and_press_operating_cost: number;
  late_delivery_penalties: number;
  wip_holding_cost: number;
  direct_labor_and_overtime_cost?: number;
  variable_production_cost: number;
  weekly_fixed_overhead: number;
  total_operating_cost: number;
  gross_profit: number;
  gross_margin_pct: number;
  net_operating_profit: number;
  net_margin_pct: number;
}

export interface SavingsBreakdown {
  purge_scrap_saved: number;
  energy_and_operating_saved: number;
  avoided_late_penalties: number;
  wip_holding_saved: number;
  regrind_blend_savings: number;
  labor_and_overtime_saved?: number;
}

export interface OrderProfitabilityItem {
  order_id: string;
  customer: string;
  sku_name: string;
  quantity_pcs: number;
  unit_selling_price: number;
  discount_pct: number;
  order_revenue: number;
  direct_resin_cost: number;
  allocated_energy_cost: number;
  allocated_purge_cost: number;
  late_penalty: number;
  net_order_profit: number;
  order_margin_pct: number;
  scheduled: boolean;
}

export interface FinancialReport {
  currency: Currency;
  annual_operating_weeks: number;
  scrap_regrind_recovery_pct: number;
  baseline: PlanFinancials;
  optimized: PlanFinancials;
  unlocked_capacity_hours: number;
  unlocked_capacity_revenue_potential: number;
  total_weekly_savings: number;
  profit_lift_pct: number;
  savings_breakdown: SavingsBreakdown;
  monthly_projected_savings: number;
  annual_projected_savings: number;
  order_profitability: OrderProfitabilityItem[];
}

export interface WorkerWeek {
  worker_id: string;
  name: string;
  role: WorkerRole;
  cells: string[];
  shifts_worked: number;
  weekly_hours: number;
  regular_hours: number;
  overtime_hours: number;
  night_shifts: number;
  labor_cost: number;
  preference_matches: number;
}

export interface ShiftDemandCell {
  day: number;
  shift: string;
  role: WorkerRole;
  required: number;
  scheduled: number;
  reasons: string[];
  mold_change: boolean;
  active_presses: number;
  uncertified_presses: string[];
}

export interface WorkforceKpis {
  regular_labor_cost: number;
  overtime_cost: number;
  total_labor_cost: number;
  regular_hours: number;
  overtime_hours: number;
  total_hours: number;
  coverage_pct: number;
  changeover_readiness_pct: number;
  preference_match_pct: number;
  understaffed_slots: number;
  headcount_gap: number;
  night_spread: number;
  violations: number;
  worst_slot?: string | null;
  role_coverage_pct: Record<string, number>;
}

export interface WorkforcePlan {
  rosters: WorkerWeek[];
  demand: ShiftDemandCell[];
  kpis: WorkforceKpis;
}

export interface WorkforceCallout {
  role?: WorkerRole | null;
  count?: number;
  day: number;
  worker_ids?: string[];
}

export interface WorkforceResult {
  currency: Currency;
  ramadan_mode: boolean;
  shift_names: string[];
  shift_hours: number;
  shift_windows: Record<string, string>;
  status: string;
  solve_time_ms: number;
  objective: number;
  baseline_objective: number;
  optimized: WorkforcePlan;
  baseline: WorkforcePlan;
  constraints_verified: ConstraintCheck[];
  baseline_constraints_verified: ConstraintCheck[];
  all_hard_constraints_passed: boolean;
  labor_cost_saved: number;
  overtime_hours_cut: number;
  callouts_applied: string[];
  reference_kpis?: WorkforceKpis | null;
  notes: string[];
}

export type RiskSeverity = "critical" | "elevated" | "watch" | "healthy";
export type RiskCategory =
  | "late_export"
  | "resin_stockout"
  | "press_bottleneck"
  | "mold_shot_limit"
  | "workforce_fragility"
  | "warehouse_congestion";

export interface RiskAlert {
  alert_id: string;
  category: RiskCategory;
  severity: "critical" | "elevated" | "watch";
  entity_type: "order" | "resin" | "press" | "mold" | "shift" | "container";
  entity_id: string;
  title_en: string;
  title_ar: string;
  detail_en: string;
  detail_ar: string;
  metric_label: string;
  metric_value: string;
  financial_exposure: number;
  suggested_prompt_en: string;
  suggested_prompt_ar: string;
}

export interface ResinDepletionClock {
  resin_code: ResinCode;
  starting_virgin_kg: number;
  consumed_virgin_plus_purge_kg: number;
  remaining_virgin_kg: number;
  utilization_pct: number;
  projected_stockout_hr?: number | null;
  coverage_hrs_remaining: number;
  status: RiskSeverity;
}

export interface RiskRadarReport {
  overall_risk_score: number;
  risk_level: RiskSeverity;
  critical_count: number;
  elevated_count: number;
  watch_count: number;
  total_financial_exposure: number;
  export_at_risk_count: number;
  tightest_slack_order_id?: string | null;
  tightest_slack_hrs?: number | null;
  resin_clocks: ResinDepletionClock[];
  alerts: RiskAlert[];
}

export interface SolveResult {
  run_id: string;
  created_at: string;
  dataset_name: string;
  currency: Currency;
  fx_egp_per_sar: number;
  status: "OPTIMAL" | "FEASIBLE" | "INFEASIBLE" | "UNKNOWN" | "MODEL_INVALID";
  solve_time_ms: number;
  objective: number;
  best_bound: number;
  gap_pct: number;
  active_engine?: EngineMode;
  validation: ValidationReport;
  applied_scenarios: AppliedScenario[];
  optimized: SchedulePlan;
  baseline: SchedulePlan;
  scorecard: Scorecard;
  financials: FinancialReport;
  audit: {
    inputs_sha256: string;
    schedule_sha256: string;
    weights: Record<string, number>;
    config: SolverConfig;
    solver_params: Record<string, unknown>;
    ortools_version: string;
    constraints_verified: ConstraintCheck[];
    baseline_constraints_verified: ConstraintCheck[];
    all_hard_constraints_passed: boolean;
  };
  workforce?: WorkforceResult | null;
  risk_radar?: RiskRadarReport | null;
}

export interface StrategyComparisonRow {
  metric: string;
  strategy_a: string;
  strategy_b: string;
  delta: string;
}

export interface StrategyComparison {
  strategy_a_name: string;
  strategy_b_name: string;
  strategy_a_weights: Record<string, number>;
  strategy_b_weights: Record<string, number>;
  rows: StrategyComparisonRow[];
  recommended_strategy: string;
}

export interface BottleneckInsight {
  target_id: string;
  target_type: string;
  headline: string;
  facts: string[];
  recommendation: string;
}

export interface FinancialTradeoffSummary {
  headline_en: string;
  headline_ar: string;
  cost_paid_label_en: string;
  cost_paid_label_ar: string;
  cost_paid_amount: number;
  value_protected_label_en: string;
  value_protected_label_ar: string;
  value_protected_amount: number;
  net_financial_gain: number;
  currency: Currency;
  is_positive_net: boolean;
}

export interface CopilotTiming {
  gemini_ms: number;
  solver_ms: number;
  total_ms: number;
}

export interface CopilotResult {
  reply: string;
  action: string;
  tool_calls_executed: string[];
  config: SolverConfig;
  dataset?: PlantDataset | null;
  plant_state?: PlantDataset | null;
  weights?: {
    w_changeover_scrap: number;
    w_otif: number;
    w_energy_cost: number;
    w_working_capital: number;
    workforce?: {
      w_labor_cost: number;
      w_coverage: number;
      w_fairness: number;
    };
  } | null;
  toggles?: {
    avoid_peak_tariff_hrs: boolean;
    ramadan_shift_mode: boolean;
    autonomous_pm_window: boolean;
    container_sync_enabled?: boolean;
  } | null;
  result?: SolveResult | null;
  production_result?: SolveResult | null;
  workforce_result?: WorkforceResult | null;
  risk_radar?: RiskRadarReport | null;
  comparison?: StrategyComparison | null;
  bottleneck?: BottleneckInsight | null;
  financial_tradeoff_summary?: FinancialTradeoffSummary | null;
  timing: CopilotTiming;
  source: string;
  quota_limited?: boolean;
  active_engine?: EngineMode;
}

export interface BacktestPeriodMetrics {
  purge_scrap_kg: number;
  purge_scrap_cost: number;
  changeover_hrs: number;
  changeover_downtime_cost: number;
  overtime_hrs: number;
  overtime_cost: number;
  late_hours: number;
  export_penalty_cost: number;
  total_avoidable_waste_cost: number;
}

export interface BacktestDeltaMetrics {
  purge_scrap_saved_kg: number;
  purge_scrap_saved_cost: number;
  purge_scrap_cut_pct: number;
  changeover_hrs_freed: number;
  changeover_cut_pct: number;
  overtime_hrs_cut: number;
  overtime_cost_saved: number;
  late_hours_avoided: number;
  export_penalties_avoided: number;
  extra_sellable_units_unlocked: number;
  extra_sellable_tons_unlocked: number;
  extra_output_margin_unlocked: number;
  direct_cost_savings_1month: number;
  total_cash_left_on_floor_1month: number;
  annualized_cash_left_on_floor: number;
  estimated_monthly_subscription_cost: number;
  estimated_payback_days: number;
}

export interface BacktestPressRow {
  press_id: string;
  orders_count: number;
  actual_changeover_hrs: number;
  optimized_changeover_hrs: number;
  unlocked_hrs: number;
  actual_purge_scrap_kg: number;
  optimized_purge_scrap_kg: number;
  scrap_saved_kg: number;
}

export interface BacktestOrderRow {
  order_id: string;
  customer: string;
  sku_name: string;
  resin: string;
  color: string;
  qty_units: number;
  actual_press_id: string;
  optimized_press_id: string;
  actual_changeover_hrs: number;
  optimized_changeover_hrs: number;
  actual_purge_scrap_kg: number;
  optimized_purge_scrap_kg: number;
  actual_late_hours: number;
  optimized_late_hours: number;
}

export interface BacktestReplayReport {
  source_label: string;
  period_days: number;
  orders_analyzed: number;
  currency: Currency;
  fx_egp_per_sar: number;
  solve_time_ms: number;
  solver_status: string;
  actual: BacktestPeriodMetrics;
  optimized: BacktestPeriodMetrics;
  actual_vs_optimized: BacktestDeltaMetrics;
  press_breakdown: BacktestPressRow[];
  order_comparison: BacktestOrderRow[];
}

export interface GuidedSetupRequest {
  plant_name: string;
  primary_process: "Injection" | "BlowMolding" | "Extrusion" | "Hybrid";
  operating_model: "MTO" | "MTS" | "Hybrid";
  currency: Currency;
  press_count: number;
  tonnage_tier: "small_med" | "heavy" | "mixed";
  backup_press_enabled: boolean;
  backup_speed_factor: number;
  standard_pm_duration_hrs: number;
  light_to_dark_priority: "strict" | "balanced";
  min_batch_run_hrs: number;
  max_regrind_allowance_pct: number;
  shift_pattern: "3x8h" | "2x12h" | "ramadan_4x6h";
  avoid_peak_tariff_hrs: boolean;
  max_weekly_hours_cap: number;
  container_sync_enabled: boolean;
  fg_storage_capacity_tons: number;
}

export interface ReadinessChecklistItem {
  item_id: string;
  title_en: string;
  title_ar: string;
  detail_en: string;
  detail_ar: string;
  erp_history_needed: boolean;
  status: string;
}

export interface GuidedSetupResponse {
  workspace_id: string;
  dataset: PlantDataset;
  config: SolverConfig;
  result: SolveResult;
  readiness_checklist: ReadinessChecklistItem[];
}

export interface AppliedScenarioDelta {
  id: string;
  appliedAt: string;
  prompt?: string;
  beforeRiskScore: number;
  afterRiskScore: number;
  beforeExportsAtRisk: number;
  afterExportsAtRisk: number;
  beforeCoveragePct: number;
  afterCoveragePct: number;
  beforeUnderstaffedSlots: number;
  afterUnderstaffedSlots: number;
  beforeWorkersCount: number;
  afterWorkersCount: number;
  workersAdded: number;
  beforeScrapKg: number;
  afterScrapKg: number;
  beforeExposure: number;
  afterExposure: number;
  currency: Currency;
  fxEgpPerSar: number;
  ceilingNoteEn?: string | null;
  ceilingNoteAr?: string | null;
}

export interface AuthStatus {
  auth_enabled: boolean;
  authenticated: boolean;
  client_label: string | null;
  session_id: string | null;
  instant_demo_enabled: boolean;
  is_admin?: boolean;
  active_engine?: EngineMode;
  env_default_engine?: EngineMode;
  is_engine_override?: boolean;
}

export interface AdminEngineModeStatus {
  active_engine: EngineMode;
  env_default_engine: EngineMode;
  is_override: boolean;
  engine_override?: EngineMode | null;
  sandbox_id?: string;
  di_standards: string[];
}

export interface AdminEngineSwitchDelta {
  prev_engine: EngineMode;
  new_engine: EngineMode;
  solve_time_ms: number;
  weekly_savings: number;
  otif_pct: number;
}

export interface AdminEngineModeSwitchResponse extends AdminEngineModeStatus {
  switch_delta: AdminEngineSwitchDelta;
  dataset: PlantDataset;
  config: SolverConfig;
  result: SolveResult;
  workforce?: WorkforceResult | null;
  financials: FinancialReport;
  risk_radar?: RiskRadarReport | null;
  validation: ValidationReport;
}

export type PinnedSlotId = "A" | "B" | "C";

export interface PinnedScenario {
  id: string;
  slot: PinnedSlotId;
  label: string;
  createdAt: string;
  dataset: PlantDataset;
  solverConfig: SolverConfig;
  result: SolveResult;
}

export interface AuditLogItem {
  run_id: string;
  created_at: string;
  dataset_name: string;
  currency: Currency;
  status: string;
  solve_time_ms: number;
  inputs_sha256: string;
  schedule_sha256: string;
  ramadan_shift_mode: boolean;
  avoid_peak_tariff_hrs: boolean;
  weights: Record<string, number>;
  scorecard_summary: {
    cash_savings: number;
    cash_savings_pct: number;
    purge_scrap_kg_saved: number;
    changeover_hours_saved: number;
    otif_pct: number;
    oee_pct: number;
  };
  all_hard_constraints_passed: boolean;
}

export interface WorkspaceSummary {
  workspace_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface PlantWorkspace {
  workspace_id: string;
  name: string;
  currency?: Currency;
  created_at: string;
  updated_at: string;
  dataset: PlantDataset;
  config: SolverConfig;
}

export type CheckpointTriggerSource =
  | "copilot"
  | "ctp_commit"
  | "workspace_save"
  | "manual"
  | "initial_seed";

export interface DecisionCheckpoint {
  id: string;
  checkpoint_id: string;
  sandbox_id: string;
  access_code: string;
  created_at: string;
  trigger_source: CheckpointTriggerSource | string;
  title_en: string;
  title_ar: string;
  risk_score: number;
  weekly_savings: number;
  otif_pct: number;
  currency: Currency;
  orders_count?: number;
  workers_count?: number;
}

export interface CheckpointsListResponse {
  storage_backend: "postgres" | "sqlite_fallback";
  pool_config: {
    pool_size: number;
    max_overflow: number;
    pool_pre_ping: boolean;
  };
  checkpoints: DecisionCheckpoint[];
}

export interface CheckpointRestoreResponse {
  restored: boolean;
  storage_backend: "postgres" | "sqlite_fallback";
  checkpoint: DecisionCheckpoint;
  dataset: PlantDataset;
  config: SolverConfig;
  result: SolveResult;
  workforce?: WorkforceResult | null;
  financials: FinancialReport;
  risk_radar?: RiskRadarReport | null;
  validation: ValidationReport;
}

export type CTPVerdict = "ON_TIME" | "LATE" | "INFEASIBLE";

export interface CTPQuoteRequest {
  customer: string;
  sku_name: string;
  mold_id: string;
  qty_units: number;
  part_weight_g?: number | null;
  resin?: ResinCode | null;
  color: PlasticColor;
  target_due_hour: number;
  unit_price?: number | null;
  is_export: boolean;
  max_regrind_pct: number;
  allow_peak_or_overtime: boolean;
  currency?: Currency;
  dataset?: PlantDataset | null;
  config?: SolverConfig | null;
  current_result?: SolveResult | null;
}

export interface CTPFinancialImpact {
  currency: Currency;
  gross_revenue: number;
  offered_unit_price: number;
  direct_resin_cost: number;
  extra_purge_scrap_kg: number;
  extra_purge_cost: number;
  extra_changeover_hrs: number;
  extra_changeover_cost: number;
  extra_electricity_cost: number;
  extra_overtime_labor_cost: number;
  extra_wip_holding_cost: number;
  extra_late_penalty_cost: number;
  total_marginal_cost: number;
  net_profit_contribution: number;
  margin_pct: number;
  min_breakeven_unit_price: number;
}

export interface CTPBumpedOrder {
  order_id: string;
  customer: string;
  sku_name: string;
  old_end_hr: number;
  new_end_hr: number;
  due_hr: number;
  delay_hrs: number;
  breaches_cutoff: boolean;
  is_export: boolean;
}

export interface CTPQuoteResult {
  verdict: CTPVerdict;
  order_id: string;
  customer: string;
  sku_name: string;
  mold_id: string;
  mold_name: string;
  resin_code: ResinCode;
  color: PlasticColor;
  qty_units: number;
  part_weight_g: number;
  gross_weight_kg: number;
  est_run_hrs: number;
  assigned_press_id?: string | null;
  assigned_press_name?: string | null;
  scheduled_start_hr?: number | null;
  scheduled_end_hr?: number | null;
  target_due_hour: number;
  slack_or_delay_hrs: number;
  financial_impact: CTPFinancialImpact;
  bumped_orders: CTPBumpedOrder[];
  export_cutoffs_breached: number;
  risk_score_before: number;
  risk_score_after: number;
  solve_time_ms: number;
  tradeoff_summary_en: string;
  tradeoff_summary_ar: string;
  candidate_order: ProductionOrder;
}

export interface CTPCommitResponse {
  committed: boolean;
  order_id: string;
  checkpoint: DecisionCheckpoint;
  dataset: PlantDataset;
  config: SolverConfig;
  result: SolveResult;
  workforce?: WorkforceResult | null;
  financials: FinancialReport;
  risk_radar?: RiskRadarReport | null;
  validation: ValidationReport;
}

export interface WhatsAppDispatchRequest {
  scope: "full_week" | "day_shift";
  day: number;
  shift: string;
  language: Lang;
  dataset?: PlantDataset | null;
  config?: SolverConfig | null;
  result?: SolveResult | null;
}

export interface WhatsAppDispatchResponse {
  scope: string;
  day: number;
  shift: string;
  language: Lang;
  plant_name: string;
  window_label: string;
  jobs_included: number;
  crew_assigned_count: number;
  open_gaps_count: number;
  message_text: string;
  whatsapp_url: string;
}
