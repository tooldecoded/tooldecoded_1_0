"""Views for manufacturer URL import."""

import json
from typing import Dict

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from product_management.services.manufacturer_import import (
    build_preview,
    execute_import,
    get_parser_for_url,
)
from product_management.services.manufacturer_import.mapper import ManufacturerDataMapper
from product_management.forms.manufacturer_import import (
    ImportPreviewForm,
    ManufacturerImportForm,
)
from product_management.views import _ensure_feature_enabled, _ensure_superuser, _dashboard_context


@require_http_methods(["GET", "POST"])
def manufacturer_import_view(request):
    """Handle manufacturer URL import - fetch and parse, then show preview."""
    _ensure_feature_enabled()
    _ensure_superuser(request)
    
    if request.method == "POST":
        form = ManufacturerImportForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data["manufacturer_url"]
            
            try:
                # Get parser and parse URL
                parser = get_parser_for_url(url)
                if not parser:
                    messages.error(request, "No parser available for this manufacturer.")
                    context = _dashboard_context(request, active_tab="import", import_form=form)
                    return render(request, "product_management/dashboard.html", context)
                
                parsed_data = parser.parse(url)
                
                if not parsed_data.is_valid():
                    errors = "; ".join(parsed_data.parsing_errors) if parsed_data.parsing_errors else "Unknown parsing error"
                    messages.error(request, f"Failed to parse product page: {errors}")
                    context = _dashboard_context(request, active_tab="import", import_form=form)
                    return render(request, "product_management/dashboard.html", context)
                
                # Build preview
                preview = build_preview(parsed_data)
                
                # Store preview data in session for approval (serialize properly - Django sessions auto-serialize)
                request.session['import_preview'] = {
                    'parsed_data': {
                        'product_name': parsed_data.product_name or '',
                        'sku': parsed_data.sku or '',
                        'brand': parsed_data.brand or '',
                        'description': parsed_data.description or '',
                        'specifications': dict(parsed_data.specifications),  # Ensure it's a plain dict
                        'features': list(parsed_data.features),
                        'included_items': list(parsed_data.included_items),
                        'image_url': parsed_data.image_url or '',
                        'categories': list(parsed_data.categories),
                        'source_url': parsed_data.source_url or '',
                    },
                    'preview_status': preview.status,
                    'existing_product_id': str(preview.existing_product.id) if preview.existing_product else None,
                    'existing_component_id': str(preview.existing_component.id) if preview.existing_component else None,
                }
                request.session.modified = True
                
                # Render preview page
                context = {
                    'page_title': 'Import Preview',
                    'preview': preview,
                    'import_form': ImportPreviewForm(),
                }
                return render(request, "product_management/import/preview.html", context)
                
            except Exception as e:
                messages.error(request, f"Import error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Form invalid
        context = _dashboard_context(request, active_tab="import", import_form=form)
        return render(request, "product_management/dashboard.html", context)
    
    # GET request - show form
    form = ManufacturerImportForm()
    context = _dashboard_context(request, active_tab="import", import_form=form)
    return render(request, "product_management/dashboard.html", context)


@require_POST
def import_preview_approve_view(request):
    """Approve and execute import."""
    _ensure_feature_enabled()
    _ensure_superuser(request)
    
    # Get preview data from session
    preview_data = request.session.get('import_preview')
    if not preview_data:
        messages.error(request, "Preview data not found. Please start over.")
        return redirect("product_management:manufacturer_import")
    
    try:
        # Reconstruct parsed data
        from product_management.services.manufacturer_import import ParsedProductData
        parsed_data = ParsedProductData(**preview_data['parsed_data'])
        
        # Rebuild preview (with existing items if any)
        preview = build_preview(parsed_data)
        if preview_data.get('existing_product_id'):
            from toolanalysis.models import Products
            preview.existing_product = Products.objects.filter(id=preview_data['existing_product_id']).first()
        if preview_data.get('existing_component_id'):
            from toolanalysis.models import Components
            preview.existing_component = Components.objects.filter(id=preview_data['existing_component_id']).first()
        
        # Execute import
        result = execute_import(preview, user=request.user)
        
        # Clear session
        if 'import_preview' in request.session:
            del request.session['import_preview']
        
        # Success message
        if result.was_update:
            messages.success(
                request,
                f"Updated product '{result.product.name}' and component '{result.component.name}'. "
                f"Added {result.attributes_created} attributes and {result.features_created} features."
            )
        else:
            messages.success(
                request,
                f"Successfully imported '{result.product.name}' ({result.product.sku}) with "
                f"{result.attributes_created} attributes and {result.features_created} features."
            )
        
        return redirect("product_management:dashboard")
        
    except Exception as e:
        messages.error(request, f"Import execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect("product_management:manufacturer_import")


@require_http_methods(["GET"])
def import_preview_cancel_view(request):
    """Cancel import and clear preview."""
    if 'import_preview' in request.session:
        del request.session['import_preview']
    messages.info(request, "Import cancelled.")
    return redirect("product_management:manufacturer_import")

