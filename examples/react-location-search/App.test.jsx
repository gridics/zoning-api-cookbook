// @vitest-environment jsdom
import React from 'react';
import { afterEach, test, expect, vi } from 'vitest';
import { render, fireEvent, screen, cleanup, act, waitFor } from '@testing-library/react';
import { App } from './App.jsx';
import { LocationSearchTextbox } from './LocationSearchTextbox.jsx';
import { createClient, fixtureSuggestion, fixtureResult } from '../browser-location-autocomplete/client.mjs';

afterEach(() => { cleanup(); vi.useRealTimers(); });
const type = query => fireEvent.change(screen.getByRole('combobox'), { target: { value: query } });
const debounce = () => act(async () => { await vi.advanceTimersByTimeAsync(300); });

test('public React debounces, reuses a session, resolves by keyboard, clears and renews', async () => {
  vi.useFakeTimers();
  const calls = [];
  const apiClient = {
    suggest: async (query, options, request) => { calls.push({ operation: 'suggest', query, options, ...request }); return { suggestions: [fixtureSuggestion, { ...fixtureSuggestion, name: '200 Example Ave', gridics_id: 'second-choice' }] }; },
    retrieve: async (id, request) => { calls.push({ operation: 'retrieve', id, ...request }); return fixtureResult; },
  };
  render(<App apiClient={apiClient} />);
  type('10'); await debounce(); expect(calls).toHaveLength(0);
  type('100'); type('100 E'); await debounce(); expect(calls).toHaveLength(1); expect(calls[0].query).toBe('100 E');
  type('100 Example'); await debounce(); expect(calls[1].sessionToken).toBe(calls[0].sessionToken);
  expect(calls[0].options).toEqual({ country: 'US', limit: 5, proximity: [-80, 25] });
  fireEvent.keyDown(screen.getByRole('combobox'), { key: 'ArrowUp' });
  expect(screen.getAllByRole('option')[1].getAttribute('aria-selected')).toBe('true');
  await act(async () => { fireEvent.keyDown(screen.getByRole('combobox'), { key: 'Enter' }); });
  expect(calls[2].id).toBe('second-choice'); expect(calls[2].sessionToken).toBe(calls[0].sessionToken);
  expect(screen.getByText('parcel_example_001')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Clear search' }));
  expect(screen.queryByText('parcel_example_001')).toBeNull(); expect(document.activeElement).toBe(screen.getByRole('combobox'));
  type('new address'); await debounce(); expect(calls[3].sessionToken).not.toBe(calls[0].sessionToken);
  fireEvent.keyDown(screen.getByRole('combobox'), { key: 'Escape' }); expect(screen.queryAllByRole('option')).toHaveLength(0);
});

test('cancelled suggestions cannot replace newer React results', async () => {
  vi.useFakeTimers(); let resolveOld; let oldSignal;
  const apiClient = { suggest: (query, _options, request) => {
    if (query === 'old address') { oldSignal = request.signal; return new Promise(resolve => { resolveOld = resolve; }); }
    return Promise.resolve({ suggestions: [{ ...fixtureSuggestion, name: 'Newest address' }] });
  }, retrieve: async () => fixtureResult };
  render(<App apiClient={apiClient} />); type('old address'); await debounce(); type('new address'); expect(oldSignal.aborted).toBe(true); await debounce();
  await act(async () => resolveOld({ suggestions: [{ ...fixtureSuggestion, name: 'Stale address' }] }));
  expect(screen.getByRole('option').textContent).toContain('Newest address'); expect(screen.queryByText('Stale address')).toBeNull();
});

test('unmount cancels retrieval and prevents resolved callbacks', async () => {
  vi.useFakeTimers(); let finish; let retrieveSignal; const onResolved = vi.fn();
  const apiClient = { suggest: async () => ({ suggestions: [fixtureSuggestion] }), retrieve: (_id, request) => { retrieveSignal = request.signal; return new Promise(resolve => { finish = resolve; }); } };
  const { unmount } = render(<LocationSearchTextbox apiClient={apiClient} onResolved={onResolved} />);
  type('100 Example'); await debounce(); fireEvent.click(screen.getByRole('option')); unmount(); expect(retrieveSignal.aborted).toBe(true);
  await act(async () => finish(fixtureResult)); expect(onResolved).not.toHaveBeenCalled();
});

test('fixture APN, empty and quota states require no network or credentials', async () => {
  vi.useFakeTimers(); const apiClient = createClient();
  const { unmount } = render(<App apiClient={apiClient} />); type('000000000001'); await debounce(); expect(screen.getByRole('option').textContent).toContain('APN match');
  type('empty'); await debounce(); expect(screen.getByRole('status').textContent).toBe('No results found.'); unmount();
  render(<App apiClient={createClient({ errorStatus: 429 })} />); type('100 Example'); await debounce(); expect(screen.getByRole('status').textContent).toMatch(/quota/i);
});

test('safe public API error discards raw server details and renews the session', async () => {
  const observed = [];
  const apiClient = createClient({ fixture: false, publishableToken: 'gpk_test_SYNTHETIC', fetcher: async (url, request) => {
    observed.push({ url, ...request });
    return { ok: false, status: 400, json: async () => ({ messages: ['location_session_mismatch'], provider_details: 'DO_NOT_DISPLAY' }) };
  } });
  render(<App apiClient={apiClient} />); type('100 Example'); await waitFor(() => expect(screen.getByRole('status').textContent).toMatch(/Start a new search/));
  const firstSession = new URL(observed[0].url).searchParams.get('session_token');
  type('200 Example'); await waitFor(() => expect(observed).toHaveLength(2));
  expect(new URL(observed[1].url).searchParams.get('session_token')).not.toBe(firstSession);
  expect(screen.queryByText(/DO_NOT_DISPLAY/)).toBeNull(); expect(observed[0].headers).toEqual({ 'X-Gridics-Publishable-Key': 'gpk_test_SYNTHETIC' });
});

test('browser build rejects secret credential class before producing assets', async () => {
  const { spawnSync } = await import('node:child_process');
  const result = spawnSync(process.execPath, ['node_modules/vite/bin/vite.js', 'build'], { cwd: process.cwd(), env: { ...process.env, VITE_GRIDICS_PUBLISHABLE_TOKEN: 'gk_REJECTED' }, encoding: 'utf8' });
  expect(result.status).not.toBe(0); expect(result.stderr).toMatch(/publishable token/); expect(result.stderr).not.toContain('gk_REJECTED');
});
