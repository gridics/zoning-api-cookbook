import React, { useMemo, useState } from 'react';
import { LocationSearchTextbox } from '../react-location-search/LocationSearchTextbox.jsx';
import { createClient } from '../browser-location-autocomplete/client.mjs';
import { createZoningClient } from './zoning-client.mjs';
import './style.css';

const fixture = import.meta.env.VITE_FIXTURE !== 'false';
const defaultLocationClient = createClient({
  fixture,
  baseUrl: import.meta.env.VITE_GRIDICS_API_BASE_URL,
  publishableToken: import.meta.env.VITE_GRIDICS_PUBLISHABLE_TOKEN
});
const defaultZoningClient = createZoningClient({
  fixture,
  proxyUrl: import.meta.env.VITE_ZONING_PROXY_URL
});

export function App({ apiClient = defaultLocationClient, zoningClient = defaultZoningClient }) {
  const [property, setProperty] = useState(null);
  const [zoning, setZoning] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onResolved(next) {
    setProperty(next);
    setZoning(null);
    setError('');
    setLoading(true);
    try {
      setZoning(await zoningClient.getZoning(next));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to load zoning.');
    } finally {
      setLoading(false);
    }
  }

  const coords = useMemo(() => property?.geometry?.coordinates?.join(', ') ?? 'Not returned', [property]);

  return <main>
    <header className="hero">
      <p className="eyebrow">Gridics developer example</p>
      <h1>Zoning Explorer</h1>
      <p>Resolve an address or APN, inspect the canonical parcel, then present zoning and development facts without exposing a secret API key in the browser.</p>
    </header>

    <section className="search-card">
      <LocationSearchTextbox apiClient={apiClient} onResolved={onResolved} onClear={() => { setProperty(null); setZoning(null); setError(''); }} />
    </section>

    <div className="grid">
      <section className="panel" aria-label="Property">
        <h2>Property</h2>
        {property ? <dl>
          <dt>Address</dt><dd>{property.properties.full_address}</dd>
          <dt>Parcel</dt><dd>{property.properties.parcel_id ?? 'Not returned'}</dd>
          <dt>APN</dt><dd>{property.properties.apn ?? 'Not returned'}</dd>
          <dt>Coordinates</dt><dd>{coords}</dd>
          <dt>County / region</dt><dd>{property.properties.context?.county?.name ?? '—'} / {property.properties.context?.region?.name ?? '—'}</dd>
        </dl> : <p>Search and select a property to begin.</p>}
      </section>

      <section className="panel zoning" aria-label="Zoning">
        <h2>Zoning</h2>
        {loading && <p role="status">Loading zoning…</p>}
        {error && <p role="alert">{error}</p>}
        {zoning && <><div className="district"><span>District</span><strong>{zoning.district ?? 'Not returned'}</strong></div>
          <p>{zoning.description ?? 'No description returned.'}</p>
          <div className="facts">{(zoning.rules ?? []).map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
          <div className="capacity"><span>Development capacity</span><strong>{zoning.development?.max_buildable_area ?? zoning.development?.status ?? 'Unavailable'}</strong></div>
          <p className="provenance">{zoning.provenance ?? 'Preserve source and request provenance from your server response.'}</p>
        </>}
        {!zoning && !loading && !error && <p>Zoning appears after property resolution.</p>}
      </section>
    </div>
  </main>;
}
