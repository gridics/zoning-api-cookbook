import { randomUUID } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'recipes/manifest.json'), 'utf8'));
const transient = new Set([429, 502, 503]);

function loadDotenv() {
  const filename = path.join(ROOT, '.env');
  if (!fs.existsSync(filename)) return;
  for (const raw of fs.readFileSync(filename, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const index = line.indexOf('=');
    const key = line.slice(0, index).trim();
    const value = line.slice(index + 1).trim().replace(/^['"]|['"]$/g, '');
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

function variables(overrides = {}) {
  const result = Object.fromEntries(Object.entries(manifest.defaults).map(([key, value]) => [key, process.env[key] ?? String(value)]));
  const mapping = { market_id: 'GRIDICS_MARKET_ID', place_id: 'GRIDICS_PLACE_ID', parcel_id: 'GRIDICS_PARCEL_ID', apn: 'GRIDICS_APN', address: 'GRIDICS_ADDRESS', postal_code: 'GRIDICS_POSTAL_CODE' };
  for (const [key, value] of Object.entries(overrides)) if (mapping[key] && value != null) result[mapping[key]] = String(value);
  return result;
}

function substitute(value, vars) {
  if (typeof value === 'string') return value.replace(/\$\{([A-Z0-9_]+)\}/g, (all, key) => vars[key] ?? all);
  if (Array.isArray(value)) return value.map((item) => substitute(item, vars));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== null).map(([key, item]) => [key, substitute(item, vars)]));
  return value;
}

function errorMessage(status, payload) {
  const detail = Array.isArray(payload?.messages) ? payload.messages.join('; ') : 'request failed';
  const hints = { 401: 'check GRIDICS_API_KEY', 403: 'check the Organization plan, capability, and county entitlement', 404: 'the resource was not found or is hidden outside the entitled scope', 409: 'the property locator is ambiguous', 422: 'check request fields, locator, units, and canonical IDs', 429: 'a rate, quota, or spending control was reached', 502: 'the upstream property service failed temporarily', 503: 'authorization, catalog, usage, or release state is temporarily unavailable' };
  return `HTTP ${status}: ${detail}. ${hints[status] ?? 'inspect the redacted request ID and response'}`;
}

async function request(baseUrl, apiKey, step, dryRun) {
  const url = new URL(step.path, `${baseUrl.replace(/\/$/, '')}/`);
  for (const [key, value] of Object.entries(step.query ?? {})) url.searchParams.set(key, String(value));
  const summary = { method: step.method, url: url.toString(), headers: { 'x-api-key': '[REDACTED]' }, ...(step.body ? { body: step.body } : {}) };
  if (dryRun) return { name: step.name, status: 'dry_run', request: summary };
  let last;
  for (let attempt = 1; attempt <= (step.max_attempts ?? 3); attempt += 1) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 20_000);
      const response = await fetch(url, { method: step.method, headers: { 'x-api-key': apiKey, Accept: 'application/json', 'User-Agent': 'zoning-api-cookbook/nodejs', ...(step.body ? { 'Content-Type': 'application/json' } : {}) }, body: step.body ? JSON.stringify(step.body) : undefined, signal: controller.signal });
      clearTimeout(timer);
      let payload;
      try { payload = await response.json(); } catch { payload = { status: 'ERROR', messages: ['non-JSON response'] }; }
      if (response.ok) return { name: step.name, status: 'ok', http_status: response.status, request_id: response.headers.get('x-request-id'), data: payload };
      last = { name: step.name, status: 'error', http_status: response.status, error: errorMessage(response.status, payload), data: payload };
      if (!transient.has(response.status) || attempt === (step.max_attempts ?? 3)) return last;
      const retryAfter = Number(response.headers.get('retry-after'));
      await new Promise((resolve) => setTimeout(resolve, Number.isFinite(retryAfter) && retryAfter > 0 ? Math.min(retryAfter * 1000, 5000) : 250 * (2 ** (attempt - 1))));
    } catch (error) {
      last = { name: step.name, status: 'error', http_status: null, error: `network error: ${error.message}` };
      if (attempt === (step.max_attempts ?? 3)) return last;
      await new Promise((resolve) => setTimeout(resolve, 250 * (2 ** (attempt - 1))));
    }
  }
  return last;
}

function locationStep(step, results, vars, session) {
  const mode = vars.GRIDICS_LOCATION_MODE;
  if (mode === 'forward' && step.name !== 'suggest_1') return null;
  const query = { q: vars.GRIDICS_LOCATION_QUERY, limit: vars.GRIDICS_LOCATION_LIMIT };
  for (const name of ['country', 'language', 'proximity', 'bbox']) {
    const value = vars[`GRIDICS_LOCATION_${name.toUpperCase()}`];
    if (value) query[name] = value;
  }
  if (mode === 'forward') return { ...step, name: 'forward', path: '/v2/locations/forward', query, max_attempts: 1 };
  query.session_token = session;
  if (step.name === 'retrieve') {
    const suggestions = results.at(-1)?.data?.suggestions ?? [];
    if (!suggestions.length) return null;
    return { ...step, path: `/v2/locations/retrieve/${encodeURIComponent(suggestions[0].gridics_id)}`, query: { session_token: session }, max_attempts: 1 };
  }
  return { ...step, query, max_attempts: 1 };
}
function locationReport(results) {
  const suggestions = results.filter(item => item.name.startsWith('suggest')).at(-1)?.data?.suggestions ?? [];
  const resolved = results.find(item => ['retrieve', 'forward'].includes(item.name))?.data;
  return { kind: 'location_search', session_token: results[0]?.session_token ?? null, mode: results[0]?.name === 'forward' ? 'forward' : 'suggest_retrieve', suggestions,
    features: resolved?.features ?? [], state: results.some(item => item.status === 'error') ? 'error' : resolved?.features?.length > 1 ? 'ambiguous' : (resolved?.features?.length || suggestions.length) ? 'resolved' : 'no_match',
    provenance: results.map(item => ({ step: item.name, status: item.status, request_id: item.request_id ?? item.data?.response_id ?? null })) };
}

function appraiserStep(step, results, vars) {
  step.max_attempts = 1;
  if (step.name === 'property') {
    const locator = process.env.GRIDICS_LOCATOR ?? 'address';
    if (!['address', 'apn', 'parcel_id'].includes(locator)) throw new Error('GRIDICS_LOCATOR must be address, apn or parcel_id');
    if (locator !== 'address') { delete step.body.address; step.body[locator] = vars[locator === 'apn' ? 'GRIDICS_APN' : 'GRIDICS_PARCEL_ID']; }
  } else if (step.name === 'zoning' && results[0]?.status === 'ok') {
    const subject = results[0].data.data;
    if (!subject.id || !subject.place_id || subject.market_ids?.length !== 1) throw new Error('Lookup did not establish one canonical parcel/Place/Market; clarify before zoning');
    step.body = { group_id: subject.id, place_id: subject.place_id, market_id: subject.market_ids[0] };
  }
  return step;
}

function appraiserReport(results) {
  const data = (index) => results[index]?.status === 'ok' ? results[index]?.data?.data ?? null : null;
  const subject = data(0), zoning = data(1), fields = subject?.fields ?? {};
  const address = fields['parcel.address'] ?? subject?.address ?? null;
  const apn = fields['parcel.apn'] ?? subject?.identifiers?.apn ?? subject?.apn ?? null;
  const code = fields['zoning.code'] ?? subject?.zoning_code ?? null;
  const unknowns = ['zoning description', 'development capacity', 'permitted uses (retrieve separately when authorized)'];
  if (address === null) unknowns.push('address');
  if (apn === null) unknowns.push('APN');
  if (code === null) unknowns.push('zoning designation');
  if ((fields['parcel.lot_area'] ?? subject?.lot_area ?? null) === null) unknowns.push('lot area');
  const envelopes = (zoning?.buildings ?? []).map((b) => b.Envelope ?? {});
  if (!envelopes.some((e) => ['PrincipalMaxHeight', 'TotalBuildingHeightFeet'].some((k) => e[k] != null))) unknowns.push('height');
  if (!envelopes.some((e) => ['EffectivePFrontSetbackPrincipal', 'EffectivePSideSetback', 'EffectivePRearSetback'].some((k) => e[k] != null))) unknowns.push('setbacks');
  if (!zoning) unknowns.push('zoning response');
  const provenance = results.map((r) => ({ step: r.name, status: r.status, request_id: r.request_id ?? r.data?.meta?.request_id ?? null }));
  const boundary = 'Factual Gridics data summary; not a formal appraisal, title opinion, legal advice, binding zoning determination or permit assurance.';
  const display = (v) => v == null ? 'unknown' : String(v).replaceAll('\n', ' ').replaceAll('`', '');
  const markdown = '# Gridics appraisal subject summary\n\n' + [
    'Address: ' + display(address), 'Parcel: ' + display(subject?.id), 'APN: ' + display(apn), 'Zoning designation: ' + display(code),
    'Request IDs: ' + provenance.map((r) => display(r.request_id)).join(', '), 'Unknown/unavailable: ' + unknowns.join('; '), boundary,
  ].join('\n') + '\n';
  return { kind: 'appraiser_zoning', property: subject, zoning, provenance, retrieved_at: new Date().toISOString(), unknowns, professional_boundary: boundary, markdown };
}

function workflow(recipeId, results) {
  const payload = (index) => results[index]?.data?.data ?? null;
  if (recipeId === '18') return locationReport(results);
  if (recipeId === '17') return appraiserReport(results);
  if (recipeId === '06') { const rows = results.flatMap((item) => item.data?.data ?? []); return { kind: 'bounded_export', rows, row_count: rows.length, pages: results.length, complete: !results.at(-1)?.data?.pagination?.next_cursor }; }
  if (recipeId === '10') return { kind: 'portfolio_enrichment', rows: results.map((item, index) => ({ row_id: `portfolio-${String(index + 1).padStart(3, '0')}`, status: item.status, property: payload(index) })) };
  if (recipeId === '11') { const blocked = results.some((item) => item.status === 'unavailable'); return { kind: 'redevelopment_screen', assessment_status: blocked ? 'capability_blocked' : 'review_required', candidates: blocked ? [] : payload(1), legal_conclusion: false }; }
  if (recipeId === '12') return { kind: 'retail_shortlist', candidates: payload(1) ?? [], scoring: 'customer_defined', excluded_datasets: ['demographics', 'traffic', 'competitors', 'drive_times', 'rent', 'availability'] };
  if (recipeId === '13') return { kind: 'property_factsheet', property: payload(0), zoning: payload(1), provenance: results.map((item) => ({ step: item.name, request_id: item.request_id ?? item.data?.meta?.request_id ?? null })), customer_notes: null };
  if (recipeId === '14') return { kind: 'property_snapshot', property: payload(0), comparison_semantics: 'observed API response; not an ordinance effective-date record' };
  if (recipeId === '15') { const property = payload(0), zoning = payload(1); return { kind: 'due_diligence_screen', overall: 'needs_review', rule_version: 'example-v1', criteria: [{ name: 'property_resolved', status: property ? 'meets' : 'needs_review' }, { name: 'zoning_available', status: zoning ? 'meets' : 'needs_review' }], facts: { property, zoning }, legal_conclusion: false }; }
  return null;
}

export async function execute(recipeId, overrides = {}) {
  loadDotenv();
  const recipe = manifest.recipes.find((item) => item.id === recipeId);
  if (!recipe) return [2, { status: 'error', error: `unknown recipe ${recipeId}` }];
  const dryRun = process.env.GRIDICS_DRY_RUN === '1';
  const fixture = process.env.GRIDICS_FIXTURE_MODE === '1';
  const baseUrl = process.env.GRIDICS_API_BASE_URL ?? manifest.api.default_base_url;
  const apiKey = process.env.GRIDICS_API_KEY ?? '';
  if (!dryRun && !apiKey) return [2, { status: 'error', error: 'GRIDICS_API_KEY is required; see README.md#get-an-api-key' }];
  const vars = variables(overrides);
  const results = [];
  let failed = false;
  const locationSession = randomUUID();
  for (const rawStep of recipe.steps) {
    let step = substitute(rawStep, vars);
    if (recipeId === '18') { step = locationStep(step, results, vars, locationSession); if (!step) continue; }
    if (recipeId === '17') {
      try { step = appraiserStep(step, results, vars); }
      catch (error) { results.push({name: step.name, status: 'error', error: error.message}); failed = true; break; }
    }
    if (recipeId === "11" && step.name === "candidates" && !dryRun) {
      const fields = results[0]?.data?.data ?? [];
      if (!fields.some((field) => field.name === "development.max_buildable_area" && field.caller_available === true && field.selectable === true)) {
        results.push({name: step.name, status: "unavailable", http_status: null, request_sent: false, data: {messages: ["capacity_fields unavailable"]}});
        continue;
      }
    }
    let result = await request(baseUrl, apiKey, step, dryRun);
    if (recipeId === '18' && apiKey) result = JSON.parse(JSON.stringify(result).split(apiKey).join("[REDACTED]"));
    if (recipeId === '18') result.session_token = step.name === 'forward' ? null : locationSession;
    if (result.status === 'error') {
      if (step.optional && result.http_status === 403) result.status = 'unavailable'; else failed = true;
    }
    results.push(result);
    if (failed) break;
    if (recipeId === '06' && result.status === 'ok' && !dryRun) {
      const seen = new Set();
      let cursor = result.data?.pagination?.next_cursor;
      let rowCount = Array.isArray(result.data?.data) ? result.data.data.length : 0;
      let page = 1;
      while (cursor && !seen.has(cursor) && page < 3 && rowCount < 100) {
        seen.add(cursor); page += 1;
        const nextStep = structuredClone(step);
        nextStep.name = `page_${page}`;
        nextStep.body = { ...(nextStep.body ?? {}), cursor };
        const nextResult = await request(baseUrl, apiKey, nextStep, false);
        results.push(nextResult);
        if (nextResult.status !== 'ok') { failed = true; break; }
        rowCount += Array.isArray(nextResult.data?.data) ? nextResult.data.data.length : 0;
        cursor = nextResult.data?.pagination?.next_cursor;
      }
    }
  }
  const output = { status: failed ? 'error' : 'ok', recipe: recipeId, title: recipe.title, execution: dryRun ? 'dry_run' : fixture ? 'fixture' : 'live', api_base_url: baseUrl, request_count: results.filter((item) => item.status !== 'dry_run' && item.request_sent !== false).length, results };
  const derived = workflow(recipeId, results); if (derived) output.workflow = derived;
  return [failed ? 1 : 0, output];
}

const tools = [
  ['gridics_verify_credential', 'Verify the server-side Gridics API key', '01', {}],
  ['gridics_list_counties', 'List entitled counties in a Market', '02', { market_id: { type: 'string' } }],
  ['gridics_lookup_property', 'Look up one property in an entitled county', '03', { place_id: { type: 'string' }, address: { type: 'string' }, postal_code: { type: 'string' } }],
  ['gridics_search_parcels', 'Run a bounded simple county parcel search', '05', { place_id: { type: 'string' } }],
  ['gridics_get_zoning', 'Get zoning for one known parcel', '04', { market_id: { type: 'string' }, place_id: { type: 'string' }, parcel_id: { type: 'string' } }],
];

async function mcpResponse(message) {
  if (message.method === 'notifications/initialized') return null;
  if (message.method === 'initialize') return { jsonrpc: '2.0', id: message.id, result: { protocolVersion: '2025-06-18', capabilities: { tools: {} }, serverInfo: { name: 'gridics-api-cookbook', version: '1.0.0' } } };
  if (message.method === 'tools/list') return { jsonrpc: '2.0', id: message.id, result: { tools: tools.map(([name, description, , properties]) => ({ name, description, inputSchema: { type: 'object', properties, additionalProperties: false } })) } };
  if (message.method === 'tools/call') {
    const tool = tools.find(([name]) => name === message.params?.name);
    if (!tool) return { jsonrpc: '2.0', id: message.id, error: { code: -32602, message: 'unknown or disallowed tool' } };
    const [code, output] = await execute(tool[2], message.params?.arguments ?? {});
    return { jsonrpc: '2.0', id: message.id, result: { content: [{ type: 'text', text: JSON.stringify(output) }], structuredContent: output, isError: code !== 0 } };
  }
  return { jsonrpc: '2.0', id: message.id, error: { code: -32601, message: 'method not found' } };
}

async function mcpServer() {
  const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of input) {
    try { const response = await mcpResponse(JSON.parse(line)); if (response) process.stdout.write(`${JSON.stringify(response)}\n`); }
    catch (error) { process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id: null, error: { code: -32603, message: error.message } })}\n`); }
  }
  return 0;
}

export async function run(recipeId) {
  if (process.argv.includes('--mcp')) return mcpServer();
  const [code, output] = await execute(recipeId);
  process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
  return code;
}
