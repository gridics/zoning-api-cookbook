import React from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App } from './App.jsx';

afterEach(cleanup);

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
