import React, { useState } from 'react';
import { LocationSearchTextbox } from './LocationSearchTextbox.jsx';
import './style.css';
import { createClient } from '../browser-location-autocomplete/client.mjs';
const client = createClient({ fixture: import.meta.env.VITE_FIXTURE !== 'false', baseUrl: import.meta.env.VITE_GRIDICS_API_BASE_URL, publishableToken: import.meta.env.VITE_GRIDICS_PUBLISHABLE_TOKEN, errorStatus: Number(import.meta.env.VITE_FIXTURE_ERROR_STATUS ?? 0) });
export function App({ apiClient = client }) {
  const [property, setProperty] = useState(null);
  return <main>
    <h1>Find a Gridics property</h1><p>Search an address or APN and select the matching property.</p>
    <LocationSearchTextbox apiClient={apiClient} onResolved={setProperty} onClear={() => setProperty(null)} />
    <section aria-label="Resolved property"><h2>Resolved property</h2>{property ? <dl>
      <dt>Address</dt><dd>{property.properties.full_address}</dd><dt>Parcel</dt><dd>{property.properties.parcel_id ?? 'Not returned'}</dd>
      <dt>APN</dt><dd>{property.properties.apn ?? 'Not returned'}</dd><dt>Longitude, latitude</dt><dd>{property.geometry?.coordinates?.join(', ') ?? 'Not returned'}</dd>
      <dt>County / region</dt><dd>{property.properties.context?.county?.name} / {property.properties.context?.region?.name}</dd>
    </dl> : <p>Select a property to view canonical details.</p>}</section>
  </main>;
}
