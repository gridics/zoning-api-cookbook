import { randomUUID } from 'node:crypto';
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
type Step = { max_attempts?: number; name: string; method: string; path: string; query?: Record<string, string>; body?: Json; optional?: boolean };
type Recipe = { id: string; title: string; steps: Step[] };
type Manifest = { api: { default_base_url: string }; defaults: Record<string, string>; recipes: Recipe[] };
type Result = { request_sent?: boolean; session_token?: string | null; name: string; status: string; http_status?: number | null; request_id?: string | null; data?: Json; error?: string; request?: Json };

function findRoot(): string {
  const candidates = [process.cwd(), path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../.."), path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..")];
  for (const candidate of candidates) {
    let current = candidate;
    while (path.dirname(current) !== current) {
      if (fs.existsSync(path.join(current, "recipes", "manifest.json"))) return current;
      current = path.dirname(current);
    }
  }
  throw new Error("Unable to locate recipes/manifest.json");
}
const ROOT = findRoot();
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, "recipes/manifest.json"), "utf8")) as Manifest;

function loadDotenv(): void {
  const file = path.join(ROOT, ".env");
  if (!fs.existsSync(file)) return;
  for (const raw of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const index = line.indexOf("=");
    const key = line.slice(0, index).trim();
    const value = line.slice(index + 1).trim().replace(/^['"]|['"]$/g, "");
    process.env[key] ??= value;
  }
}

function substitute(value: Json, variables: Record<string, string>): Json {
  if (typeof value === "string") return value.replace(/\$\{([A-Z0-9_]+)\}/g, (all, key: string) => variables[key] ?? all);
  if (Array.isArray(value)) return value.map((item) => substitute(item, variables));
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== null).map(([key, item]) => [key, substitute(item, variables)]));
  return value;
}

function errorMessage(status: number, payload: Json): string {
  const object = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
  const messages = Array.isArray(object.messages) ? object.messages.join("; ") : "request failed";
  const hints: Record<number, string> = { 401: "check GRIDICS_API_KEY", 403: "check plan, capability, and county entitlement", 404: "not found or hidden outside entitled scope", 409: "ambiguous locator", 422: "invalid request fields or IDs", 429: "rate, quota, or spending control reached", 502: "temporary upstream failure", 503: "temporary authorization, catalog, usage, or release failure" };
  return `HTTP ${status}: ${messages}. ${hints[status] ?? "inspect the redacted request ID"}`;
}

async function call(baseUrl: string, apiKey: string, step: Step, dryRun: boolean): Promise<Result> {
  const url = new URL(step.path, `${baseUrl.replace(/\/$/, "")}/`);
  for (const [key, value] of Object.entries(step.query ?? {})) url.searchParams.set(key, value);
  if (dryRun) return { name: step.name, status: "dry_run", request: { method: step.method, url: url.toString(), headers: { "x-api-key": "[REDACTED]" }, ...(step.body ? { body: step.body } : {}) } };
  let last: Result = { name: step.name, status: "error", error: "request did not run" };
  for (let attempt = 1; attempt <= (step.max_attempts ?? 3); attempt += 1) {
    try {
      const response = await fetch(url, { method: step.method, headers: { "x-api-key": apiKey, Accept: "application/json", "User-Agent": "zoning-api-cookbook/typescript", ...(step.body ? { "Content-Type": "application/json" } : {}) }, body: step.body ? JSON.stringify(step.body) : undefined, signal: AbortSignal.timeout(20_000) });
      let payload: Json;
      try { payload = await response.json() as Json; } catch { payload = { status: "ERROR", messages: ["non-JSON response"] }; }
      if (response.ok) return { name: step.name, status: "ok", http_status: response.status, request_id: response.headers.get("x-request-id"), data: payload };
      last = { name: step.name, status: "error", http_status: response.status, error: errorMessage(response.status, payload), data: payload };
      if (![429, 502, 503].includes(response.status) || attempt === (step.max_attempts ?? 3)) return last;
    } catch (error) {
      last = { name: step.name, status: "error", http_status: null, error: `network error: ${error instanceof Error ? error.message : String(error)}` };
      if (attempt === (step.max_attempts ?? 3)) return last;
    }
    await new Promise((resolve) => setTimeout(resolve, 250 * 2 ** (attempt - 1)));
  }
  return last;
}

function locationStep(step: Step, results: Result[], vars: Record<string, string>, session: string): Step | null {
  const mode = vars.GRIDICS_LOCATION_MODE;
  if (mode === 'forward' && step.name !== 'suggest_1') return null;
  const query: Record<string, string> = { q: vars.GRIDICS_LOCATION_QUERY ?? '100 Example Ave', limit: vars.GRIDICS_LOCATION_LIMIT ?? '5' };
  for (const name of ['country', 'language', 'proximity', 'bbox']) {
    const value = vars[`GRIDICS_LOCATION_${name.toUpperCase()}`];
    if (value) query[name] = value;
  }
  if (mode === 'forward') return { ...step, name: 'forward', path: '/v2/locations/forward', query, max_attempts: 1 };
  query.session_token = session;
  if (step.name === 'retrieve') {
    const suggestions = (results.at(-1)?.data as any)?.suggestions ?? [];
    if (!suggestions.length) return null;
    return { ...step, path: `/v2/locations/retrieve/${encodeURIComponent(suggestions[0].gridics_id)}`, query: { session_token: session }, max_attempts: 1 };
  }
  return { ...step, query, max_attempts: 1 };
}
function locationReport(results: Result[]): Json {
  const suggestions = (results.filter(item => item.name.startsWith('suggest')).at(-1)?.data as any)?.suggestions ?? [];
  const resolved: any = results.find(item => ['retrieve', 'forward'].includes(item.name))?.data;
  return { kind: 'location_search', session_token: results[0]?.session_token ?? null, mode: results[0]?.name === 'forward' ? 'forward' : 'suggest_retrieve', suggestions,
    features: resolved?.features ?? [], state: results.some(item => item.status === 'error') ? 'error' : resolved?.features?.length > 1 ? 'ambiguous' : (resolved?.features?.length || suggestions.length) ? 'resolved' : 'no_match',
    provenance: results.map(item => ({ step: item.name, status: item.status, request_id: item.request_id ?? (item.data as any)?.response_id ?? null })) };
}

function appraiserStep(step: Step, results: Result[], vars: Record<string, string>): Step {
  step.max_attempts = 1;
  if (step.name === 'property') {
    const locator = process.env.GRIDICS_LOCATOR ?? 'address';
    if (!['address', 'apn', 'parcel_id'].includes(locator)) throw new Error('GRIDICS_LOCATOR must be address, apn or parcel_id');
    const body = step.body as Record<string, Json>;
    if (locator !== 'address') { delete body.address; body[locator] = vars[locator === 'apn' ? 'GRIDICS_APN' : 'GRIDICS_PARCEL_ID']!; }
  } else if (step.name === 'zoning' && results[0]?.status === 'ok') {
    const subject = (results[0].data as Record<string, Json>).data as Record<string, Json>;
    if (!subject.id || !subject.place_id || !Array.isArray(subject.market_ids) || subject.market_ids.length !== 1) throw new Error('Lookup did not establish one canonical parcel/Place/Market; clarify before zoning');
    step.body = { group_id: subject.id, place_id: subject.place_id, market_id: subject.market_ids[0]! };
  }
  return step;
}

function appraiserReport(results: Result[]): Json {
  const data = (index: number) => results[index]?.status === 'ok' ? (results[index].data as Record<string, Json>)?.data ?? null : null;
  const subject = data(0) as Record<string, Json> | null, zoning = data(1) as Record<string, Json> | null, fields = (subject?.fields ?? {}) as Record<string, Json>;
  const address = fields['parcel.address'] ?? subject?.address ?? null;
  const apn = fields['parcel.apn'] ?? (subject?.identifiers as Record<string, Json>)?.apn ?? subject?.apn ?? null;
  const code = fields['zoning.code'] ?? subject?.zoning_code ?? null;
  const unknowns = ['zoning description', 'development capacity', 'permitted uses (retrieve separately when authorized)'];
  if (address === null) unknowns.push('address');
  if (apn === null) unknowns.push('APN');
  if (code === null) unknowns.push('zoning designation');
  if ((fields['parcel.lot_area'] ?? subject?.lot_area ?? null) === null) unknowns.push('lot area');
  const envelopes = ((zoning?.buildings ?? []) as Record<string, Json>[]).map((b) => (b.Envelope ?? {}) as Record<string, Json>);
  if (!envelopes.some((e) => ['PrincipalMaxHeight', 'TotalBuildingHeightFeet'].some((k) => e[k] != null))) unknowns.push('height');
  if (!envelopes.some((e) => ['EffectivePFrontSetbackPrincipal', 'EffectivePSideSetback', 'EffectivePRearSetback'].some((k) => e[k] != null))) unknowns.push('setbacks');
  if (!zoning) unknowns.push('zoning response');
  const provenance = results.map((r) => ({ step: r.name, status: r.status, request_id: r.request_id ?? ((r.data as Record<string, Json>)?.meta as Record<string, Json>)?.request_id ?? null }));
  const boundary = 'Factual Gridics data summary; not a formal appraisal, title opinion, legal advice, binding zoning determination or permit assurance.';
  const display = (v: Json | undefined) => v == null ? 'unknown' : String(v).replaceAll('\n', ' ').replaceAll('`', '');
  const markdown = '# Gridics appraisal subject summary\n\n' + [
    'Address: ' + display(address), 'Parcel: ' + display(subject?.id), 'APN: ' + display(apn), 'Zoning designation: ' + display(code),
    'Request IDs: ' + provenance.map((r) => display(r.request_id)).join(', '), 'Unknown/unavailable: ' + unknowns.join('; '), boundary,
  ].join('\n') + '\n';
  return { kind: 'appraiser_zoning', property: subject, zoning, provenance, retrieved_at: new Date().toISOString(), unknowns, professional_boundary: boundary, markdown };
}

function workflow(recipeId: string, results: Result[]): Json | null {
  const payload = (index: number): Json => {
    const envelope = results[index]?.data;
    return envelope && typeof envelope === "object" && !Array.isArray(envelope) ? envelope.data ?? null : null;
  };
  if (recipeId === "18") return locationReport(results);
  if (recipeId === "17") return appraiserReport(results);
  if (recipeId === "06") { const rows = results.flatMap((item) => { const value = payload(results.indexOf(item)); return Array.isArray(value) ? value : []; }); return { kind: "bounded_export", rows, row_count: rows.length, pages: results.length, complete: true }; }
  if (recipeId === "10") return { kind: "portfolio_enrichment", rows: results.map((item, index) => ({ row_id: `portfolio-${String(index + 1).padStart(3, "0")}`, status: item.status, property: payload(index) })) };
  if (recipeId === "11") { const blocked = results.some((item) => item.status === "unavailable"); return { kind: "redevelopment_screen", assessment_status: blocked ? "capability_blocked" : "review_required", candidates: blocked ? [] : payload(1), legal_conclusion: false }; }
  if (recipeId === "12") return { kind: "retail_shortlist", candidates: payload(1) ?? [], scoring: "customer_defined", excluded_datasets: ["demographics", "traffic", "competitors", "drive_times", "rent", "availability"] };
  if (recipeId === "13") return { kind: "property_factsheet", property: payload(0), zoning: payload(1), provenance: results.map((item) => ({ step: item.name, request_id: item.request_id ?? null })), customer_notes: null };
  if (recipeId === "14") return { kind: "property_snapshot", property: payload(0), comparison_semantics: "observed API response; not an ordinance effective-date record" };
  if (recipeId === "15") { const property = payload(0), zoning = payload(1); return { kind: "due_diligence_screen", overall: "needs_review", rule_version: "example-v1", criteria: [{ name: "property_resolved", status: property ? "meets" : "needs_review" }, { name: "zoning_available", status: zoning ? "meets" : "needs_review" }], facts: { property, zoning }, legal_conclusion: false }; }
  return null;
}

export async function execute(recipeId: string, overrides: Record<string, Json> = {}): Promise<[number, Json]> {
  loadDotenv();
  const recipe = manifest.recipes.find((item) => item.id === recipeId);
  if (!recipe) return [2, { status: "error", error: `unknown recipe ${recipeId}` }];
  const dryRun = process.env.GRIDICS_DRY_RUN === "1";
  const fixture = process.env.GRIDICS_FIXTURE_MODE === "1";
  const baseUrl = process.env.GRIDICS_API_BASE_URL ?? manifest.api.default_base_url;
  const apiKey = process.env.GRIDICS_API_KEY ?? "";
  if (!dryRun && !apiKey) return [2, { status: "error", error: "GRIDICS_API_KEY is required; see README.md#get-an-api-key" }];
  const vars = Object.fromEntries(Object.entries(manifest.defaults).map(([key, value]) => [key, process.env[key] ?? value]));
  const mapping: Record<string, string> = { market_id: "GRIDICS_MARKET_ID", place_id: "GRIDICS_PLACE_ID", parcel_id: "GRIDICS_PARCEL_ID", apn: "GRIDICS_APN", address: "GRIDICS_ADDRESS", postal_code: "GRIDICS_POSTAL_CODE" };
  for (const [key, value] of Object.entries(overrides)) if (mapping[key] && value != null) vars[mapping[key]] = String(value);
  const results: Result[] = [];
  let failed = false;
  const locationSession = randomUUID();
  for (const raw of recipe.steps) {
    let step = substitute(raw as unknown as Json, vars) as Step;
    if (recipeId === "18") { const next = locationStep(step, results, vars, locationSession); if (!next) continue; step = next; }
    if (recipeId === "17") {
      try { step = appraiserStep(step, results, vars); }
      catch (error) { results.push({name: step.name, status: "error", error: String(error)}); failed = true; break; }
    }
    if (recipeId === "11" && step.name === "candidates" && !dryRun) {
      const fields = (results[0]?.data as {data?: {name: string; caller_available?: boolean; selectable?: boolean}[]} | undefined)?.data ?? [];
      if (!fields.some((field) => field.name === "development.max_buildable_area" && field.caller_available === true && field.selectable === true)) {
        results.push({name: step.name, status: "unavailable", http_status: null, request_sent: false, data: {messages: ["capacity_fields unavailable"]}});
        continue;
      }
    }
    let result = await call(baseUrl, apiKey, step, dryRun);
    if (recipeId === "18" && apiKey) result = JSON.parse(JSON.stringify(result).split(apiKey).join("[REDACTED]"));
    if (recipeId === "18") result.session_token = step.name === "forward" ? null : locationSession;
    if (result.status === "error") { if (step.optional && result.http_status === 403) result.status = "unavailable"; else failed = true; }
    results.push(result);
    if (failed) break;
    if (recipeId === "06" && result.status === "ok" && !dryRun) {
      const seen = new Set<string>();
      const firstPayload = result.data as { data?: Json[]; pagination?: { next_cursor?: string | null } } | undefined;
      let cursor = firstPayload?.pagination?.next_cursor;
      let rowCount = firstPayload?.data?.length ?? 0;
      let page = 1;
      while (cursor && !seen.has(cursor) && page < 3 && rowCount < 100) {
        seen.add(cursor); page += 1;
        const nextStep = structuredClone(step);
        nextStep.name = `page_${page}`;
        nextStep.body = { ...((nextStep.body as Record<string, Json> | undefined) ?? {}), cursor };
        const nextResult = await call(baseUrl, apiKey, nextStep, false);
        results.push(nextResult);
        if (nextResult.status !== "ok") { failed = true; break; }
        const nextPayload = nextResult.data as { data?: Json[]; pagination?: { next_cursor?: string | null } } | undefined;
        rowCount += nextPayload?.data?.length ?? 0;
        cursor = nextPayload?.pagination?.next_cursor;
      }
    }
  }
  const output: Record<string, Json> = { status: failed ? "error" : "ok", recipe: recipeId, title: recipe.title, execution: dryRun ? "dry_run" : fixture ? "fixture" : "live", api_base_url: baseUrl, request_count: results.filter((item) => item.status !== "dry_run" && item.request_sent !== false).length, results: results as unknown as Json };
  const derived = workflow(recipeId, results); if (derived) output.workflow = derived;
  return [failed ? 1 : 0, output];
}

const tools = [
  ["gridics_verify_credential", "Verify the server-side Gridics API key", "01", {}],
  ["gridics_list_counties", "List entitled counties in a Market", "02", { market_id: { type: "string" } }],
  ["gridics_lookup_property", "Look up one property", "03", { place_id: { type: "string" }, address: { type: "string" }, postal_code: { type: "string" } }],
  ["gridics_search_parcels", "Run a bounded county parcel search", "05", { place_id: { type: "string" } }],
  ["gridics_get_zoning", "Get zoning for one known parcel", "04", { market_id: { type: "string" }, place_id: { type: "string" }, parcel_id: { type: "string" } }],
] as const;

async function mcpServer(): Promise<number> {
  const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of input) {
    const message = JSON.parse(line) as { id?: Json; method?: string; params?: { name?: string; arguments?: Record<string, Json> } };
    if (message.method === "notifications/initialized") continue;
    let response: Json;
    if (message.method === "initialize") response = { jsonrpc: "2.0", id: message.id ?? null, result: { protocolVersion: "2025-06-18", capabilities: { tools: {} }, serverInfo: { name: "gridics-api-cookbook", version: "1.0.0" } } };
    else if (message.method === "tools/list") response = { jsonrpc: "2.0", id: message.id ?? null, result: { tools: tools.map(([name, description, , properties]) => ({ name, description, inputSchema: { type: "object", properties, additionalProperties: false } })) } };
    else if (message.method === "tools/call") {
      const tool = tools.find(([name]) => name === message.params?.name);
      if (!tool) response = { jsonrpc: "2.0", id: message.id ?? null, error: { code: -32602, message: "unknown or disallowed tool" } };
      else { const [code, output] = await execute(tool[2], message.params?.arguments); response = { jsonrpc: "2.0", id: message.id ?? null, result: { content: [{ type: "text", text: JSON.stringify(output) }], structuredContent: output, isError: code !== 0 } }; }
    } else response = { jsonrpc: "2.0", id: message.id ?? null, error: { code: -32601, message: "method not found" } };
    process.stdout.write(`${JSON.stringify(response)}\n`);
  }
  return 0;
}

export async function run(recipeId: string): Promise<number> {
  if (process.argv.includes("--mcp")) return mcpServer();
  const [code, output] = await execute(recipeId);
  process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
  return code;
}
