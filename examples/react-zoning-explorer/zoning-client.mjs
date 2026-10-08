const FIXTURE = {
  state: 'resolved',
  district: 'R-4',
  description: 'Synthetic residential zoning example',
  rules: [
    ['Allowed uses', 'Returned by the live zoning response'],
    ['Setbacks', 'Display returned parcel-specific values'],
    ['Height', 'Display returned parcel-specific values'],
    ['Density / FAR', 'Display returned parcel-specific values']
  ],
  development: {
    status: 'capability-aware',
    max_buildable_area: 'Shown only when returned and available'
  },
  provenance: 'Synthetic fixture — not a live zoning determination'
};

export function createZoningClient({ fixture = true, proxyUrl = '' } = {}) {
  return {
    async getZoning(property) {
      if (fixture) return structuredClone(FIXTURE);
      if (!proxyUrl) throw new Error('Set VITE_ZONING_PROXY_URL to a server-side adapter for live zoning.');
      const response = await fetch(proxyUrl, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          parcel_id: property?.properties?.parcel_id ?? null,
          apn: property?.properties?.apn ?? null,
          address: property?.properties?.full_address ?? null
        })
      });
      if (!response.ok) throw new Error('Zoning proxy returned HTTP ' + response.status);
      return response.json();
    }
  };
}
