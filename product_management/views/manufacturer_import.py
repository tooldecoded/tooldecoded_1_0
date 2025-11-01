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
    get_parser_for_brand,
)
from product_management.services.manufacturer_import.mapper import ManufacturerDataMapper
from product_management.forms.manufacturer_import import (
    ImportPreviewForm,
    ManufacturerImportForm,
    ManufacturerHTMLImportForm,
)
from product_management.views import _ensure_feature_enabled, _ensure_superuser, _dashboard_context


@require_http_methods(["GET", "POST"])
def manufacturer_import_view(request):
    """Handle manufacturer URL import - fetch and parse, then show preview."""
    _ensure_feature_enabled()
    _ensure_superuser(request)
    
    if request.method == "POST":
        # Check which form was submitted
        if "submit_url" in request.POST:
            url_form = ManufacturerImportForm(request.POST, prefix="url")
            html_form = ManufacturerHTMLImportForm(prefix="html")
            
            if url_form.is_valid() and url_form.cleaned_data.get("manufacturer_url"):
                # URL form submitted
                url = url_form.cleaned_data["manufacturer_url"]
                
                try:
                    # Detect brand from URL or use DEWALT as default
                    brand = "DEWALT"  # Default, could be enhanced to detect from URL
                    if 'dewalt' in url.lower():
                        brand = "DEWALT"
                    elif 'milwaukee' in url.lower():
                        brand = "Milwaukee"
                    elif 'makita' in url.lower():
                        brand = "Makita"
                    
                    parser = get_parser_for_brand(brand)
                    if not parser:
                        messages.error(request, f"Could not create parser for brand: {brand}")
                        context = _dashboard_context(request, active_tab="import", import_form=url_form, import_html_form=html_form)
                        return render(request, "product_management/dashboard.html", context)
                    
                    parsed_data = parser.parse(url)
                    
                    if not parsed_data.is_valid():
                        errors = "; ".join(parsed_data.parsing_errors) if parsed_data.parsing_errors else "Unknown parsing error"
                        messages.error(request, f"Failed to parse product page: {errors}")
                        context = _dashboard_context(request, active_tab="import", import_form=url_form, import_html_form=html_form)
                        return render(request, "product_management/dashboard.html", context)
                    
                    # Build preview and continue...
                    preview = build_preview(parsed_data)
                    
                    # Store full preview data (serializable)
                    import json
                    preview_data_serializable = {
                        'product_specifications': preview.product_specifications,
                        'component_attributes': preview.component_attributes,
                        'component_features': preview.component_features,
                        'categories': preview.categories,
                        'subcategories': preview.subcategories,
                        'itemtypes': preview.itemtypes,
                        'included_components': preview.included_components,
                    }
                    
                    request.session['import_preview'] = {
                        'parsed_data': {
                            'product_name': parsed_data.product_name or '',
                            'sku': parsed_data.sku or '',
                            'brand': parsed_data.brand or '',
                            'description': parsed_data.description or '',
                            'specifications': dict(parsed_data.specifications),
                            'features': list(parsed_data.features),
                            'included_items': list(parsed_data.included_items),
                            'image_url': parsed_data.image_url or '',
                            'categories': list(parsed_data.categories),
                            'source_url': parsed_data.source_url or '',
                            # Store extended Gemini data
                            'product_specifications': getattr(parsed_data, '_product_specifications', []),
                            'component_attributes': getattr(parsed_data, '_component_attributes', []),
                            'component_features': getattr(parsed_data, '_component_features', []),
                            'category_mappings': getattr(parsed_data, '_category_mappings', []),
                            'subcategory_mappings': getattr(parsed_data, '_subcategory_mappings', []),
                            'itemtype_mappings': getattr(parsed_data, '_itemtype_mappings', []),
                        },
                        'preview_data': preview_data_serializable,
                        'preview_status': preview.status,
                        'existing_product_id': str(preview.existing_product.id) if preview.existing_product else None,
                        'existing_component_id': str(preview.existing_component.id) if preview.existing_component else None,
                    }
                    request.session.modified = True
                    
                    # Create form with initial data from parsed data
                    import_form = ImportPreviewForm(initial={
                        'product_name': parsed_data.product_name,
                        'product_sku': parsed_data.sku,
                        'product_description': parsed_data.description or '',
                        'product_image': parsed_data.image_url or '',
                        'component_name': parsed_data.product_name,
                        'component_sku': parsed_data.sku,
                        'component_description': parsed_data.description or '',
                        'component_image': parsed_data.image_url or '',
                        'existing_product_id': preview.existing_product.id if preview.existing_product else None,
                        'existing_component_id': preview.existing_component.id if preview.existing_component else None,
                        'preview_data_json': json.dumps(preview_data_serializable),
                        'approve': True,
                    })
                    
                    context = {
                        'page_title': 'Import Preview',
                        'preview': preview,
                        'import_form': import_form,
                    }
                    return render(request, "product_management/import/preview.html", context)
                    
                except Exception as e:
                    messages.error(request, f"Import error: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # Form invalid - show errors
            context = _dashboard_context(request, active_tab="import", import_form=url_form, import_html_form=html_form)
            return render(request, "product_management/dashboard.html", context)
        
        elif "submit_html" in request.POST:
            url_form = ManufacturerImportForm(prefix="url")
            html_form = ManufacturerHTMLImportForm(request.POST, prefix="html")
            
            if html_form.is_valid():
                # HTML form submitted
                html = html_form.cleaned_data["page_source"]
                brand = html_form.cleaned_data["manufacturer_brand"]
                
                try:
                    parser = get_parser_for_brand(brand)
                    if not parser:
                        messages.error(request, f"No parser available for brand: {brand}")
                        context = _dashboard_context(request, active_tab="import", import_form=url_form, import_html_form=html_form)
                        return render(request, "product_management/dashboard.html", context)
                    
                    # Try to extract URL from HTML
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    source_url = ""
                    canonical = soup.find('link', rel='canonical')
                    if canonical and canonical.get('href'):
                        source_url = canonical.get('href')
                    else:
                        og_url = soup.find('meta', property='og:url')
                        if og_url and og_url.get('content'):
                            source_url = og_url.get('content')
                    
                    parsed_data = parser.parse_from_html(html, source_url=source_url)
                    
                    if not parsed_data.is_valid():
                        errors = "; ".join(parsed_data.parsing_errors) if parsed_data.parsing_errors else "Unknown parsing error"
                        messages.error(request, f"Failed to parse HTML: {errors}")
                        context = _dashboard_context(request, active_tab="import", import_form=url_form, import_html_form=html_form)
                        return render(request, "product_management/dashboard.html", context)
                    
                    # Build preview and continue...
                    preview = build_preview(parsed_data)
                    
                    # Store full preview data (serializable)
                    import json
                    preview_data_serializable = {
                        'product_specifications': preview.product_specifications,
                        'component_attributes': preview.component_attributes,
                        'component_features': preview.component_features,
                        'categories': preview.categories,
                        'subcategories': preview.subcategories,
                        'itemtypes': preview.itemtypes,
                        'included_components': preview.included_components,
                    }
                    
                    request.session['import_preview'] = {
                        'parsed_data': {
                            'product_name': parsed_data.product_name or '',
                            'sku': parsed_data.sku or '',
                            'brand': parsed_data.brand or '',
                            'description': parsed_data.description or '',
                            'specifications': dict(parsed_data.specifications),
                            'features': list(parsed_data.features),
                            'included_items': list(parsed_data.included_items),
                            'image_url': parsed_data.image_url or '',
                            'categories': list(parsed_data.categories),
                            'source_url': parsed_data.source_url or '',
                            # Store extended Gemini data
                            'product_specifications': getattr(parsed_data, '_product_specifications', []),
                            'component_attributes': getattr(parsed_data, '_component_attributes', []),
                            'component_features': getattr(parsed_data, '_component_features', []),
                            'category_mappings': getattr(parsed_data, '_category_mappings', []),
                            'subcategory_mappings': getattr(parsed_data, '_subcategory_mappings', []),
                            'itemtype_mappings': getattr(parsed_data, '_itemtype_mappings', []),
                        },
                        'preview_data': preview_data_serializable,
                        'preview_status': preview.status,
                        'existing_product_id': str(preview.existing_product.id) if preview.existing_product else None,
                        'existing_component_id': str(preview.existing_component.id) if preview.existing_component else None,
                    }
                    request.session.modified = True
                    
                    # Create form with initial data from parsed data
                    import_form = ImportPreviewForm(initial={
                        'product_name': parsed_data.product_name,
                        'product_sku': parsed_data.sku,
                        'product_description': parsed_data.description or '',
                        'product_image': parsed_data.image_url or '',
                        'component_name': parsed_data.product_name,
                        'component_sku': parsed_data.sku,
                        'component_description': parsed_data.description or '',
                        'component_image': parsed_data.image_url or '',
                        'existing_product_id': preview.existing_product.id if preview.existing_product else None,
                        'existing_component_id': preview.existing_component.id if preview.existing_component else None,
                        'preview_data_json': json.dumps(preview_data_serializable),
                        'approve': True,
                    })
                    
                    context = {
                        'page_title': 'Import Preview',
                        'preview': preview,
                        'import_form': import_form,
                    }
                    return render(request, "product_management/import/preview.html", context)
                    
                except Exception as e:
                    messages.error(request, f"Import error: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # Form invalid - show errors
            context = _dashboard_context(request, active_tab="import", import_form=url_form, import_html_form=html_form)
            return render(request, "product_management/dashboard.html", context)
    
    # GET request - show forms
    url_form = ManufacturerImportForm(prefix="url")
    html_form = ManufacturerHTMLImportForm(prefix="html")
    context = _dashboard_context(request, active_tab="import", import_form=url_form, import_html_form=html_form)
    return render(request, "product_management/dashboard.html", context)


@require_POST
def import_preview_approve_view(request):
    """Approve and execute import with optional field edits."""
    _ensure_feature_enabled()
    _ensure_superuser(request)
    
    # Get preview data from session
    preview_data = request.session.get('import_preview')
    if not preview_data:
        messages.error(request, "Preview data not found. Please start over.")
        return redirect("product_management:manufacturer_import")
    
    # Get form with edited values
    form = ImportPreviewForm(request.POST)
    if not form.is_valid():
        # If form invalid, rebuild preview with errors
        from product_management.services.manufacturer_import import ParsedProductData, build_preview
        parsed_data = ParsedProductData(**preview_data['parsed_data'])
        preview = build_preview(parsed_data)
        context = {
            'page_title': 'Import Preview',
            'preview': preview,
            'import_form': form,
        }
        return render(request, "product_management/import/preview.html", context)
    
    try:
        import json
        # Reconstruct parsed data and apply form edits
        from product_management.services.manufacturer_import import ParsedProductData
        parsed_data = ParsedProductData(**preview_data['parsed_data'])
        
        # Override with form values (user can edit before approval)
        parsed_data.product_name = form.cleaned_data.get('product_name') or parsed_data.product_name
        parsed_data.sku = form.cleaned_data.get('product_sku') or parsed_data.sku
        
        # Use component description/image for product, or override if provided separately
        product_desc = form.cleaned_data.get('product_description') or parsed_data.description
        product_img = form.cleaned_data.get('product_image') or parsed_data.image_url
        
        # Component values (can differ from product)
        component_name = form.cleaned_data.get('component_name') or parsed_data.product_name
        component_sku = form.cleaned_data.get('component_sku') or parsed_data.sku
        component_desc = form.cleaned_data.get('component_description') or parsed_data.description
        component_img = form.cleaned_data.get('component_image') or parsed_data.image_url
        
        # Update parsed_data with edited values
        parsed_data.product_name = form.cleaned_data.get('product_name') or parsed_data.product_name
        parsed_data.sku = form.cleaned_data.get('product_sku') or parsed_data.sku
        parsed_data.description = component_desc  # Use component description as default
        parsed_data.image_url = component_img  # Use component image as default
        
        # Store product-specific overrides separately for mapper
        parsed_data._product_description = product_desc
        parsed_data._product_image_url = product_img
        parsed_data._component_name = component_name
        parsed_data._component_sku = component_sku
        parsed_data._component_description = component_desc
        parsed_data._component_image_url = component_img
        
        # Rebuild preview (with existing items if any)
        preview = build_preview(parsed_data)
        if preview_data.get('existing_product_id'):
            from toolanalysis.models import Products
            preview.existing_product = Products.objects.filter(id=preview_data['existing_product_id']).first()
        if preview_data.get('existing_component_id'):
            from toolanalysis.models import Components
            preview.existing_component = Components.objects.filter(id=preview_data['existing_component_id']).first()
        
        # Apply edited preview data from form (if provided)
        preview_data_json = form.cleaned_data.get('preview_data_json', '')
        if preview_data_json:
            try:
                edited_preview_data = json.loads(preview_data_json)
                # Override preview with edited values
                if 'product_specifications' in edited_preview_data:
                    preview.product_specifications = edited_preview_data['product_specifications']
                if 'component_attributes' in edited_preview_data:
                    preview.component_attributes = edited_preview_data['component_attributes']
                if 'component_features' in edited_preview_data:
                    preview.component_features = edited_preview_data['component_features']
                if 'categories' in edited_preview_data:
                    preview.categories = edited_preview_data['categories']
                if 'subcategories' in edited_preview_data:
                    preview.subcategories = edited_preview_data['subcategories']
                if 'itemtypes' in edited_preview_data:
                    preview.itemtypes = edited_preview_data['itemtypes']
            except (json.JSONDecodeError, ValueError):
                pass  # Use original preview data if JSON parse fails
        
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

