export const fixtureSuggestion = { name: '100 Example Ave', full_address: '100 Example Ave, Example City', place_formatted: 'Example City, Example State', matched_by: 'address', feature_type: 'address', gridics_id: 'fixture-selected', context: { county: { name: 'Example County' }, region: { name: 'Example State' } } };
export const fixtureResult = { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [-80, 25] }, properties: { ...fixtureSuggestion, parcel_id: 'parcel_example_001', apn: '000000000001' } }], response_id: 'fixture-response' };
export const messages = { 400: 'Start a new search; the session or selected result is invalid.', 401: 'Check the publishable token and its allowed origin.', 403: 'Check your plan capability and entitled coverage.', 409: 'Start a new search; the session or selected result has expired.', 422: 'Check the query and geographic hints.', 429: 'Quota or request rate limit reached. Try a new search later.', 502: 'Search is temporarily unavailable.', 503: 'Search is temporarily unavailable.' };
export function createClient({ baseUrl = 'https://api.gridics.com', publishableToken = '', fixture = true, fetcher = fetch, onRequest = () => {}, errorStatus = 0 } = {}) {
  if ((!fixture || publishableToken !== '') && !/^gpk_(test|live)_[A-Za-z0-9_-]+$/.test(publishableToken)) throw new Error('Use a scoped gpk_test_... or gpk_live_... publishable token.');
  async function request(path, query, signal) {
    if (fixture) {
      if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
      if (errorStatus) { const error = new Error(messages[errorStatus] ?? 'Search failed.'); error.code = ({ 400: 'session_invalid', 401: 'publishable_key_invalid', 403: 'feature_unavailable', 409: 'session_invalid', 422: 'invalid_query', 429: 'quota_exhausted', 502: 'service_unavailable', 503: 'service_unavailable' })[errorStatus]; throw error; }
      onRequest({ method: 'GET', endpoint: path.includes('/retrieve/') ? '/v2/locations/retrieve/{gridics_id}' : path, status: 200, session: query.session_token?.slice(0, 8) ?? null });
      return path.endsWith('/suggest') ? { suggestions: query.q.toLowerCase().includes('empty') ? [] : [{ ...fixtureSuggestion, matched_by: /^\d/.test(query.q) ? 'apn' : 'address' }], response_id: 'fixture-response' } : structuredClone(fixtureResult);
    }
    const url = new URL(path, baseUrl); for (const [key, value] of Object.entries(query)) if (value !== '' && value != null) url.searchParams.set(key, String(value));
    const response = await fetcher(url, { headers: { 'X-Gridics-Publishable-Key': publishableToken }, signal });
    onRequest({ method: 'GET', endpoint: path.includes('/retrieve/') ? '/v2/locations/retrieve/{gridics_id}' : path, status: response.status, session: query.session_token?.slice(0, 8) ?? null });
    if (!response.ok) { const payload = await response.json().catch(() => ({})); const codes = { location_search_not_included: ['feature_unavailable', 'Location Search is not included in this plan.'], geographic_scope_not_allowed: ['no_geographic_coverage', 'No entitled geographic coverage is available.'], invalid_location_session: ['session_invalid', 'Start a new search; the session has expired.'], location_session_closed: ['session_invalid', 'Start a new search; the previous session is complete.'], location_session_mismatch: ['session_invalid', 'Start a new search; the session does not match this selection.'], cursor_invalid: ['result_expired', 'Start a new search; this selection is invalid.'], invalid_location_id: ['result_expired', 'Start a new search; this selection has expired.'], location_session_call_limit: ['session_invalid', 'Start a new search; this session reached its request limit.'], quota_exceeded: ['quota_exhausted', 'Location Search quota reached.'], usage_limit_exceeded: ['quota_exhausted', 'Location Search quota reached.'], limit_exceeded: ['quota_exhausted', 'Location Search usage limit reached.'], spending_limit_exceeded: ['quota_exhausted', 'Location Search spending limit reached.'], rate_limit_exceeded: ['rate_limited', 'Too many requests. Try a new search later.'] }; const known = codes[payload.messages?.[0]]; const error = new Error(known?.[1] ?? messages[response.status] ?? 'Search failed. Please try a new search.'); error.code = known?.[0] ?? ({ 400: 'session_invalid', 401: 'publishable_key_invalid', 403: 'feature_unavailable', 409: 'session_invalid', 422: 'invalid_query', 429: 'quota_exhausted', 502: 'service_unavailable', 503: 'service_unavailable' })[response.status]; throw error; }
    return response.json();
  }
  return {
    suggest(query, options = {}, { sessionToken, signal } = {}) { return request('/v2/locations/suggest', { q: query, ...options, limit: Math.min(10, options.limit ?? 5), session_token: sessionToken }, signal); },
    retrieve(gridicsId, { sessionToken, signal } = {}) { return request(`/v2/locations/retrieve/${encodeURIComponent(gridicsId)}`, { session_token: sessionToken }, signal); },
  };
}
export class SearchInteraction {
  constructor(client, update, { delay = 275, uuid = () => crypto.randomUUID(), now = () => Date.now(), setTimer = (fn, ms) => setTimeout(fn, ms), clearTimer = (timer) => clearTimeout(timer) } = {}) { Object.assign(this, { client, update, delay, uuid, now, setTimer, clearTimer }); this.sequence = 0; this.session = null; this.rows = []; this.active = -1; }
  cancel() { this.clearTimer(this.timer); this.controller?.abort(); this.sequence++; }
  clear() { this.cancel(); this.session = null; this.rows = []; this.active = -1; this.update({ rows: [], status: '', resolved: null }); }
  search(query) {
    this.cancel(); this.rows = []; this.active = -1; this.update({ rows: [], status: '', resolved: null });
    if (!query.trim()) { this.session = null; return; }
    if (query.trim().length < 3) return;
    if (!this.session || this.now() - this.sessionStarted >= 180000) { this.session = this.uuid(); this.sessionStarted = this.now(); } const session = this.session, sequence = this.sequence;
    this.timer = this.setTimer(async () => { this.controller = new AbortController(); this.update({ status: 'Searching…' }); try {
      const result = await this.client.suggest(query.trim(), {}, { sessionToken: session, signal: this.controller.signal });
      if (sequence !== this.sequence) return; this.rows = result.suggestions; this.update({ rows: this.rows, status: this.rows.length ? `${this.rows.length} results available.` : 'No results found.' });
    } catch (error) { if (sequence === this.sequence && error.name !== 'AbortError') { this.session = null; this.update({ rows: [], status: error.message }); } } }, this.delay);
  }
  async select(index) {
    const row = this.rows[index]; if (!row) return; this.cancel(); const sequence = this.sequence, session = this.session; this.rows = []; this.update({ rows: [], status: 'Resolving…' }); this.controller = new AbortController();
    try { const result = await this.client.retrieve(row.gridics_id, { sessionToken: session, signal: this.controller.signal }); if (sequence === this.sequence) { this.session = null; this.update({ resolved: result, status: 'Property resolved.' }); } }
    catch (error) { if (sequence === this.sequence && error.name !== 'AbortError') { this.session = null; this.update({ status: error.message }); } }
  }
  key(key) { if (key === 'Escape') { this.cancel(); this.rows = []; this.update({ rows: [], status: '' }); return true; } if (!this.rows.length) return false; if (key === 'Enter') { if (this.active >= 0) this.select(this.active); return true; } if (key === 'ArrowDown' || key === 'ArrowUp') { this.active = this.active < 0 ? (key === 'ArrowDown' ? 0 : this.rows.length - 1) : (this.active + (key === 'ArrowDown' ? 1 : -1) + this.rows.length) % this.rows.length; this.update({ active: this.active }); return true; } return false; }
}
