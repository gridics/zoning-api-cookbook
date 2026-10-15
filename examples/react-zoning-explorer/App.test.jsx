import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App } from './App.jsx';
import { createZoningClient } from './zoning-client.mjs';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe('Zoning Explorer', () => {
  it('renders zoning after a resolved property is selected', async () => {
    const property = {
      properties: {full_address:'100 Example Ave', parcel_id:'parcel_example_001', apn:'000000000001', context:{county:{name:'Example County'},region:{name:'FL'}}},
      geometry:{coordinates:[-80.1,25.7]}
    };
    const apiClient = {
      suggest: async () => ({suggestions:[{gridics_id:'one',name:'100 Example Ave',full_address:'100 Example Ave'}]}),
      retrieve: async () => ({features:[property]})
    };
    const zoningClient = {getZoning: async () => ({district:'R-4',description:'Synthetic',rules:[['Height','Returned']],development:{status:'available'},provenance:'fixture'})};

    render(<App apiClient={apiClient} zoningClient={zoningClient} />);
    const input = screen.getByRole('combobox');
    fireEvent.change(input,{target:{value:'100 Example'}});
    await waitFor(() => expect(screen.getByText('100 Example Ave')).toBeTruthy());
    fireEvent.click(screen.getByText('100 Example Ave'));
    await waitFor(() => expect(screen.getByText('R-4')).toBeTruthy());
    expect(screen.getByText('parcel_example_001')).toBeTruthy();
  });
});


function pendingResult() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function delayedExplorer() {
  const properties = Object.fromEntries(['alpha', 'beta'].map((id, index) => [id, {
    properties: { full_address: `${id} Example Ave`, parcel_id: `parcel_${id}`, apn: `00000000000${index + 1}` },
    geometry: { coordinates: [-80, 25] }
  }]));
  const pending = { alpha: pendingResult(), beta: pendingResult() };
  const apiClient = {
    suggest: async query => {
      const id = query.toLowerCase().startsWith('alpha') ? 'alpha' : 'beta';
      return { suggestions: [{ gridics_id: id, name: `${id} Example Ave`, full_address: `${id} Example Ave` }] };
    },
    retrieve: async id => ({ features: [properties[id]] })
  };
  // Deliberately ignore cancellation: stale-result safety must also work for a
  // custom adapter whose underlying work cannot be cancelled.
  const zoningClient = { getZoning: vi.fn(property => pending[property.properties.parcel_id.replace('parcel_', '')].promise) };
  const view = render(<App apiClient={apiClient} zoningClient={zoningClient} />);
  async function select(id) {
    fireEvent.change(screen.getByRole('combobox'), { target: { value: id } });
    const option = await screen.findByRole('option', { name: `${id} Example Ave` });
    fireEvent.click(option);
    await waitFor(() => expect(zoningClient.getZoning.mock.calls.some(call => call[0] === properties[id])).toBe(true));
  }
  return { pending, select, zoningClient, unmount: view.unmount };
}

describe('Pending zoning selection', () => {
  it('keeps the newer property zoning when an older response finishes last', async () => {
    const { pending, select } = delayedExplorer();
    await select('alpha'); await select('beta');
    await act(async () => pending.beta.resolve({ district: 'B district' }));
    expect(screen.getByText('B district')).toBeTruthy();
    await act(async () => pending.alpha.resolve({ district: 'A district' }));
    expect(screen.queryByText('A district')).toBeNull();
    expect(screen.getByText('B district')).toBeTruthy();
    expect(screen.getByText('parcel_beta')).toBeTruthy();
  });

  it('does not restore zoning or loading after clear while a response is pending', async () => {
    const { pending, select } = delayedExplorer();
    await select('alpha');
    fireEvent.click(screen.getByRole('button', { name: 'Clear search' }));
    expect(screen.queryByText('Loading zoning…')).toBeNull();
    await act(async () => pending.alpha.resolve({ district: 'A district' }));
    expect(screen.queryByText('A district')).toBeNull();
    expect(screen.getByText('Search and select a property to begin.')).toBeTruthy();
    expect(screen.getByText('Zoning appears after property resolution.')).toBeTruthy();
  });

  it('ignores old failures without clearing the current loading state', async () => {
    const { pending, select } = delayedExplorer();
    await select('alpha'); await select('beta');
    await act(async () => pending.alpha.reject(new Error('Old request failure')));
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByText('Loading zoning…')).toBeTruthy();
    await act(async () => pending.beta.resolve({ district: 'B district' }));
    expect(screen.getByText('B district')).toBeTruthy();
    expect(screen.queryByText('Loading zoning…')).toBeNull();
  });
});


describe('Zoning request cancellation', () => {
  it('aborts pending work when a selected property is cleared or unmounted', async () => {
    const { select, zoningClient, unmount } = delayedExplorer();
    await select('alpha');
    const first = zoningClient.getZoning.mock.calls[0][1].signal;
    fireEvent.click(screen.getByRole('button', { name: 'Clear search' }));
    expect(first.aborted).toBe(true);
    await select('beta');
    const second = zoningClient.getZoning.mock.calls[1][1].signal;
    unmount();
    expect(second.aborted).toBe(true);
  });

  it('forwards cancellation to the server-adapter request', async () => {
    const controller = new AbortController();
    const fetchRequest = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => ({ district: 'Synthetic district' }) });
    const client = createZoningClient({ fixture: false, proxyUrl: 'http://localhost:8787/api/zoning' });
    await client.getZoning({ properties: { parcel_id: 'parcel_example_001', apn: '000000000001', full_address: '100 Example Ave' } }, { signal: controller.signal });
    expect(fetchRequest).toHaveBeenCalledWith('http://localhost:8787/api/zoning', expect.objectContaining({ signal: controller.signal }));
    expect(JSON.parse(fetchRequest.mock.calls[0][1].body)).toEqual({ parcel_id: 'parcel_example_001', apn: '000000000001', address: '100 Example Ave' });
  });
});
