import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import { SearchInteraction } from '../browser-location-autocomplete/client.mjs';

const defaultOptions = { country: 'US', limit: 5, proximity: [-80, 25] };

// React only renders the public, framework-neutral interaction controller.
export function LocationSearchTextbox({ apiClient, options = defaultOptions, onResolved, onClear, label = 'Address or parcel number' }) {
  const id = useId();
  const [value, setValue] = useState('');
  const [view, setView] = useState({ rows: [], active: -1, status: '' });
  const callbacks = useRef({ onResolved, onClear });
  callbacks.current = { onResolved, onClear };
  const optionsKey = JSON.stringify(options);
  const interaction = useMemo(() => new SearchInteraction({
    suggest: (query, _options, request) => apiClient.suggest(query, JSON.parse(optionsKey), request),
    retrieve: (gridicsId, request) => apiClient.retrieve(gridicsId, request),
  }, update => {
    setView(previous => ({ ...previous, ...update, ...(update.rows ? { active: -1 } : {}) }));
    if (update.resolved === null) callbacks.current.onClear?.();
    if (update.resolved) {
      const feature = update.resolved.features?.[0];
      if (feature) {
        setValue(feature.properties.full_address ?? feature.properties.name ?? '');
        callbacks.current.onResolved?.(feature);
      }
    }
  }), [apiClient, optionsKey]);
  useEffect(() => () => interaction.cancel(), [interaction]);
  const input = useRef(null);
  const listId = `${id}-results`, statusId = `${id}-status`;
  return <div className="location-search">
    <label htmlFor={id}>{label}</label>
    <div className="location-search-input"><span aria-hidden="true">⌕</span>
      <input ref={input} id={id} role="combobox" value={value} placeholder="100 Example Ave" autoComplete="off"
        aria-autocomplete="list" aria-expanded={view.rows.length > 0} aria-controls={listId} aria-describedby={statusId}
        aria-activedescendant={view.active >= 0 ? `${id}-option-${view.active}` : undefined}
        onChange={event => { setValue(event.target.value); interaction.search(event.target.value); }}
        onKeyDown={event => { if (interaction.key(event.key)) event.preventDefault(); }} />
      <button type="button" aria-label="Clear search" onClick={() => { setValue(''); interaction.clear(); input.current?.focus(); }}>×</button>
    </div>
    <ul id={listId} role="listbox" aria-label={`${label} suggestions`}>
      {view.rows.map((row, index) => <li key={row.gridics_id} id={`${id}-option-${index}`} role="option" aria-selected={view.active === index}
        onPointerDown={event => event.preventDefault()} onClick={() => interaction.select(index)}>
        <strong>{row.name}</strong><span>{[row.place_formatted, row.context?.county?.name, row.matched_by === 'apn' ? 'APN match' : null].filter(Boolean).join(' · ')}</span>
      </li>)}
    </ul>
    <p id={statusId} role="status" aria-live="polite">{view.status || 'Enter at least 3 characters.'}</p>
  </div>;
}
