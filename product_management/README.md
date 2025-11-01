# Product Management Backoffice

This app replaces the legacy `components_backoffice` flows with a consolidated product and component workspace.

## Key Capabilities

- Quick creation workflows for standalone components and linked product shells.
- Bundle assembly tools that reuse existing components.
- Product-to-component extraction with audit-backed undo.
- JSON/HTMX-friendly endpoints for type-ahead selectors.

## Cutover Notes

- Requests to `/components-backoffice/` now redirect to `/product-management/`.
- Audit history is stored in `product_management.BackofficeAudit`; undo currently supports the latest `create` action for components and products.
- After deployment run migrations: `python manage.py migrate product_management`.
- Add staff messaging and training before disabling the legacy dashboard feature flag.

## Tests

Run the focused suite with:

```
python manage.py test product_management --keepdb
```

