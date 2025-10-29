from django.db import transaction
from django.db.models import Count, Max
from decimal import Decimal
from datetime import datetime
from .models import Components, Products, PriceListings, ProductComponents, ComponentPricingHistory


def get_standalone_component_prices():
    """
    Get component prices from products that have only one component.
    Returns: {component_id: {'price': Decimal, 'date': datetime, 'product': Product, 'pricelisting': PriceListing}}
    """
    # Query products with exactly one component
    products_with_one_component = Products.objects.annotate(
        component_count=Count('productcomponents')
    ).filter(component_count=1)
    
    standalone_prices = {}
    
    for product in products_with_one_component:
        # Get the single component
        product_component = product.productcomponents_set.first()
        if not product_component:
            continue
            
        component = product_component.component
        
        # Get the latest price listing for this product
        latest_pricelisting = PriceListings.objects.filter(
            product=product
        ).order_by('-datepulled').first()
        
        if latest_pricelisting:
            standalone_prices[component.id] = {
                'price': latest_pricelisting.price,
                'date': latest_pricelisting.datepulled,
                'product': product,
                'pricelisting': latest_pricelisting
            }
    
    return standalone_prices


def calculate_prorated_prices(product, standalone_prices_dict):
    """
    Calculate prorated component prices for a multi-component product.
    Returns: {component_id: {'price': Decimal, 'weight_ratio': float, 'metadata': dict}}
    """
    # Get all components for this product
    product_components = product.productcomponents_set.all()
    
    # Check if all components have standalone prices
    missing_components = []
    for pc in product_components:
        if pc.component.id not in standalone_prices_dict:
            missing_components.append(pc.component.name)
    
    if missing_components:
        return None  # Skip if any components missing standalone prices
    
    # Get the latest price listing for this product
    latest_pricelisting = PriceListings.objects.filter(
        product=product
    ).order_by('-datepulled').first()
    
    if not latest_pricelisting:
        return None
    
    product_price = latest_pricelisting.price
    
    # Calculate total weight (sum of standalone_price * quantity)
    total_weight = Decimal('0')
    component_weights = {}
    
    for pc in product_components:
        component = pc.component
        standalone_price = standalone_prices_dict[component.id]['price']
        weight = standalone_price * pc.quantity
        component_weights[component.id] = {
            'weight': weight,
            'quantity': pc.quantity,
            'standalone_price': standalone_price
        }
        total_weight += weight
    
    if total_weight == 0:
        return None
    
    # Calculate prorated prices
    prorated_prices = {}
    
    for component_id, weight_data in component_weights.items():
        weight_ratio = float(weight_data['weight'] / total_weight)
        prorated_price = (weight_data['standalone_price'] * weight_data['quantity'] / total_weight) * product_price
        
        prorated_prices[component_id] = {
            'price': prorated_price,
            'weight_ratio': weight_ratio,
            'metadata': {
                'standalone_price': float(weight_data['standalone_price']),
                'quantity': weight_data['quantity'],
                'product_price': float(product_price),
                'total_weight': float(total_weight),
                'source_product': product.name,
                'source_pricelisting_id': latest_pricelisting.id
            }
        }
    
    return prorated_prices


@transaction.atomic
def update_all_component_pricing(dry_run=False, verbose=False):
    """
    Update all component pricing based on PriceListings data.
    Returns: dict with stats about the update process
    """
    stats = {
        'standalone_updated': 0,
        'prorated_updated': 0,
        'skipped': 0,
        'products_processed': 0,
        'errors': []
    }
    
    try:
        # Step 1: Get standalone component prices
        if verbose:
            print("Getting standalone component prices...")
        
        standalone_prices = get_standalone_component_prices()
        
        if verbose:
            print(f"Found {len(standalone_prices)} components with standalone prices")
        
        # Step 2: Update components with standalone prices
        for component_id, price_data in standalone_prices.items():
            try:
                component = Components.objects.get(id=component_id)
                
                # Only update if not using manual price
                if not component.use_manual_price:
                    if not dry_run:
                        component.calculated_price = price_data['price']
                        component.last_calculated_date = datetime.now()
                        component.price_source_product = price_data['product']
                        component.price_source_pricelisting = price_data['pricelisting']
                        component.save()
                        
                        # Create history entry
                        ComponentPricingHistory.objects.create(
                            component=component,
                            price=price_data['price'],
                            source_type='standalone',
                            source_product=price_data['product'],
                            source_pricelisting=price_data['pricelisting'],
                            metadata={
                                'calculation_date': price_data['date'].isoformat(),
                                'source': 'standalone_product'
                            }
                        )
                    
                    stats['standalone_updated'] += 1
                    
                    if verbose:
                        print(f"Updated {component.name} with standalone price: ${price_data['price']}")
                else:
                    stats['skipped'] += 1
                    if verbose:
                        print(f"Skipped {component.name} (manual price override)")
                        
            except Components.DoesNotExist:
                stats['errors'].append(f"Component {component_id} not found")
            except Exception as e:
                stats['errors'].append(f"Error updating component {component_id}: {str(e)}")
        
        # Step 3: Process multi-component products for prorated pricing
        if verbose:
            print("Processing multi-component products for prorated pricing...")
        
        # Get products with multiple components that have price listings
        products_with_multiple_components = Products.objects.annotate(
            component_count=Count('productcomponents')
        ).filter(
            component_count__gt=1,
            pricelistings__isnull=False
        ).distinct()
        
        for product in products_with_multiple_components:
            try:
                stats['products_processed'] += 1
                
                prorated_prices = calculate_prorated_prices(product, standalone_prices)
                
                if prorated_prices is None:
                    stats['skipped'] += 1
                    if verbose:
                        print(f"Skipped {product.name} (missing standalone prices or no price listing)")
                    continue
                
                # Update components with prorated prices
                for component_id, price_data in prorated_prices.items():
                    try:
                        component = Components.objects.get(id=component_id)
                        
                        # Only update if not using manual price
                        if not component.use_manual_price:
                            if not dry_run:
                                component.calculated_price = price_data['price']
                                component.last_calculated_date = datetime.now()
                                component.price_source_product = product
                                # Get the latest pricelisting for this product
                                latest_pricelisting = PriceListings.objects.filter(
                                    product=product
                                ).order_by('-datepulled').first()
                                component.price_source_pricelisting = latest_pricelisting
                                component.save()
                                
                                # Create history entry
                                ComponentPricingHistory.objects.create(
                                    component=component,
                                    price=price_data['price'],
                                    source_type='prorated',
                                    source_product=product,
                                    source_pricelisting=latest_pricelisting,
                                    metadata=price_data['metadata']
                                )
                            
                            stats['prorated_updated'] += 1
                            
                            if verbose:
                                print(f"Updated {component.name} with prorated price: ${price_data['price']:.2f} (ratio: {price_data['weight_ratio']:.3f})")
                        else:
                            stats['skipped'] += 1
                            if verbose:
                                print(f"Skipped {component.name} (manual price override)")
                                
                    except Components.DoesNotExist:
                        stats['errors'].append(f"Component {component_id} not found")
                    except Exception as e:
                        stats['errors'].append(f"Error updating component {component_id}: {str(e)}")
                        
            except Exception as e:
                stats['errors'].append(f"Error processing product {product.name}: {str(e)}")
        
        if verbose:
            print(f"\nPricing update completed:")
            print(f"  Standalone updates: {stats['standalone_updated']}")
            print(f"  Prorated updates: {stats['prorated_updated']}")
            print(f"  Skipped (manual override): {stats['skipped']}")
            print(f"  Products processed: {stats['products_processed']}")
            if stats['errors']:
                print(f"  Errors: {len(stats['errors'])}")
                for error in stats['errors']:
                    print(f"    - {error}")
        
        return stats
        
    except Exception as e:
        stats['errors'].append(f"Fatal error in pricing update: {str(e)}")
        if verbose:
            print(f"Fatal error: {str(e)}")
        return stats
