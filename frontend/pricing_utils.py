"""
Pricing calculation utilities for component pricing display system.
"""
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from toolanalysis.models import PriceListings, ProductComponents, Components, Products


def get_latest_product_pricelistings(product, days=60):
    """
    Get latest PriceListing per retailer for a product (≤60 days old).
    
    Args:
        product: Products model instance
        days: Maximum age of price listings in days (default: 60)
    
    Returns:
        dict: {retailer_id: PriceListing instance} - one most recent per retailer
    """
    cutoff_date = timezone.now().date() - timedelta(days=days)
    
    # Get all price listings within the date range
    all_listings = PriceListings.objects.filter(
        product=product,
        datepulled__gte=cutoff_date
    ).select_related('retailer').order_by('-datepulled')
    
    # Get the most recent listing per retailer
    latest_by_retailer = {}
    for listing in all_listings:
        retailer_id = listing.retailer.id if listing.retailer else None
        if retailer_id not in latest_by_retailer:
            latest_by_retailer[retailer_id] = listing
    
    return latest_by_retailer


def prorate_product_price_to_components(product, product_price):
    """
    Calculate effective component prices using weighted proration based on standalone_price.
    
    Algorithm:
    1. Calculate total "value" weight: Sum of (component.standalone_price × quantity) 
       for all components with standalone_price
    2. For components with standalone_price: weight = (standalone_price × quantity) / total_weight
    3. For components without standalone_price: equal share of remaining weight
    4. Effective component price = product_price × weight / quantity
    
    Args:
        product: Products model instance
        product_price: Decimal price of the product
    
    Returns:
        dict: {component_id: {'effective_price': Decimal, 'weight': Decimal, 'quantity': int}}
    """
    product_components = ProductComponents.objects.filter(
        product=product
    ).select_related('component')
    
    # Step 1: Calculate total weight from components with standalone_price
    total_weight = Decimal('0')
    component_data = {}
    
    for pc in product_components:
        component = pc.component
        standalone_price = component.standalone_price
        
        if standalone_price is not None:
            weighted_value = standalone_price * Decimal(pc.quantity)
            total_weight += weighted_value
            component_data[component.id] = {
                'has_price': True,
                'weighted_value': weighted_value,
                'quantity': pc.quantity,
            }
        else:
            component_data[component.id] = {
                'has_price': False,
                'weighted_value': Decimal('0'),
                'quantity': pc.quantity,
            }
    
    # Step 2 & 3: Calculate weights
    components_without_price = [
        comp_id for comp_id, data in component_data.items()
        if not data['has_price']
    ]
    
    # Allocate weights
    if total_weight > 0:
        # Components with price get weight proportional to their value
        # These weights will sum to 1.0 if all components have prices
        used_weight = Decimal('0')
        for comp_id, data in component_data.items():
            if data['has_price']:
                weight = data['weighted_value'] / total_weight
                component_data[comp_id]['weight'] = weight
                used_weight += weight
        
        # If there are components without price, they share the remaining weight equally
        if components_without_price:
            remaining_weight = Decimal('1') - used_weight
            if remaining_weight > 0:
                weight_per_component = remaining_weight / Decimal(len(components_without_price))
                for comp_id in components_without_price:
                    component_data[comp_id]['weight'] = weight_per_component
    else:
        # No components have standalone_price - equal distribution
        weight_per_component = Decimal('1') / Decimal(len(component_data)) if component_data else Decimal('0')
        for comp_id in component_data:
            component_data[comp_id]['weight'] = weight_per_component
    
    # Step 4: Calculate effective component prices
    result = {}
    for comp_id, data in component_data.items():
        weight = data.get('weight', Decimal('0'))
        quantity = data['quantity']
        
        # Effective price = (product_price * weight) / quantity
        if quantity > 0 and weight > 0:
            effective_price = (product_price * weight) / Decimal(quantity)
        else:
            effective_price = Decimal('0')
        
        result[comp_id] = {
            'effective_price': effective_price,
            'weight': weight,
            'quantity': quantity,
        }
    
    return result


def calculate_component_discounts(component, list_price, effective_price):
    """
    Calculate dollar and percentage discounts for a component.
    
    Args:
        component: Components model instance
        list_price: Decimal standalone price (list price)
        effective_price: Decimal effective price from kit
    
    Returns:
        dict: {
            'dollar_discount': Decimal or None,
            'percentage_discount': Decimal or None,
            'has_discount': bool
        }
    """
    if list_price is None or effective_price is None:
        return {
            'dollar_discount': None,
            'percentage_discount': None,
            'has_discount': False,
        }
    
    if list_price <= Decimal('0') or effective_price <= Decimal('0'):
        return {
            'dollar_discount': None,
            'percentage_discount': None,
            'has_discount': False,
        }
    
    dollar_discount = list_price - effective_price
    
    if dollar_discount > 0:
        percentage_discount = (dollar_discount / list_price) * Decimal('100')
        return {
            'dollar_discount': dollar_discount,
            'percentage_discount': percentage_discount,
            'has_discount': True,
        }
    else:
        return {
            'dollar_discount': Decimal('0'),
            'percentage_discount': Decimal('0'),
            'has_discount': False,
        }


def get_component_kit_pricing(component):
    """
    Get all products containing component with prorated prices.
    
    Args:
        component: Components model instance
    
    Returns:
        list: [
            {
                'product': Products instance,
                'product_component': ProductComponents instance,
                'pricelistings': [PriceListing instances],
                'component_pricing': {
                    'effective_price': Decimal,
                    'list_price': Decimal,
                    'discounts': dict,
                }
            },
            ...
        ]
    """
    # Get all products containing this component
    product_components = ProductComponents.objects.filter(
        component=component
    ).select_related('product').prefetch_related('product__productimages_set')
    
    result = []
    
    for pc in product_components:
        product = pc.product
        
        # Get latest pricelistings for this product
        latest_listings = get_latest_product_pricelistings(product, days=60)
        
        # Process each pricelisting
        for retailer_id, pricelisting in latest_listings.items():
            # Calculate prorated component prices
            prorated_prices = prorate_product_price_to_components(
                product, 
                pricelisting.price
            )
            
            # Get pricing data for this specific component
            component_pricing_data = prorated_prices.get(component.id)
            
            if component_pricing_data:
                effective_price = component_pricing_data['effective_price']
                list_price = component.standalone_price
                
                # Calculate discounts
                discounts = calculate_component_discounts(
                    component,
                    list_price,
                    effective_price
                )
                
                result.append({
                    'product': product,
                    'product_component': pc,
                    'pricelisting': pricelisting,
                    'component_pricing': {
                        'effective_price': effective_price,
                        'list_price': list_price,
                        'discounts': discounts,
                    }
                })
    
    return result

