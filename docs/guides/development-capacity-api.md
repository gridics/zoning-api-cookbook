# Development capacity API workflows

Development-capacity workflows are most useful when an API exposes the relevant field for the caller's geography and product capability.

The cookbook's [redevelopment screen](../../recipes/11-redevelopment-screen/) demonstrates a fail-closed pattern: discover search fields first, confirm that development.max_buildable_area is available and selectable, and only then request it.

## Why capability discovery matters

A field being present in a schema does not mean it is released for every market or subscription. Production applications should discover capabilities at runtime and present unavailable data honestly.

Use this pattern for redevelopment screening, underbuilt-parcel analysis, portfolio triage, and other development-feasibility workflows.