import os
import django
import sys
import google.generativeai as genai
import time
import json
import argparse

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

# Import your models
from toolanalysis.models import Components, ItemCategories, Brands, BatteryPlatforms, ComponentAttributes

# Parse command line arguments
parser = argparse.ArgumentParser(description='Analyze drill driver components with Gemini AI')
parser.add_argument('--skip-existing', action='store_true', 
                    help='Skip components that already have analysis data')
args = parser.parse_args()

# Configure Gemini
genai.configure(api_key="AIzaSyCBU440DFi_w0L77QPpCKpO319nSU1hLBY")
model = genai.GenerativeModel("gemini-2.5-flash")

# SKIP TRIGGER CONFIGURATION
# Change this to True/False to enable/disable skip logic
SKIP_IF_HAS_DATA = True  # Set to False to process all components regardless of existing data

# Filter for drill driver components
try:
    drill_driver_category = ItemCategories.objects.get(name__icontains="impact drivers")
    drill_driver_components = Components.objects.filter(itemcategories=drill_driver_category)
    
    # Initialize statistics counters
    total_components = 0
    skipped_components = 0
    queried_components = 0
    
    for component in drill_driver_components:
        total_components += 1
        # Gather component information
        component_info = {
            "sku": component.sku,
            "name": component.name,
            "brand": component.brand.name if component.brand else "Unknown",
            "description": component.description or "No description available",
            "battery_platforms": [bp.name for bp in component.batteryplatforms.all()],
            "battery_voltages": [str(bv.value) + "V" for bv in component.batteryvoltages.all()],
            "item_categories": [cat.name for cat in component.itemcategories.all()],
        }
        
        # Get component attributes
        attributes = ComponentAttributes.objects.filter(component=component)
        component_attributes = {attr.attribute.name: attr.value for attr in attributes}
        component_info["attributes"] = component_attributes
        
        # Check if we should skip this component
        if args.skip_existing and SKIP_IF_HAS_DATA and component.fair_price_narrative:
            print(f"⏭️  Skipping {component.sku} - already has analysis data")
            skipped_components += 1
            continue
        
        # Create input string for Gemini
        input_string = f"""# CRITICAL OUTPUT REQUIREMENTS
You MUST respond with ONLY a JSON object containing the exact fields specified below. Do not include any markdown formatting, explanations, or additional text outside the JSON.

# OBJECTIVE
Find the best target price a buyer should aim for to get a great deal on this drill driver tool. This should be ONE price - the best typical value achievable through any channel (kit proration, standalone sales, clearance, etc.).

# EVALUATION FACTORS
Evaluate from the perspective of a professional tradesperson or serious DIYer:

- Drill performance and power
- Build quality and durability  
- Features and ergonomics
- Market pricing compared to similar drills
- The existence of successor models and pricing of those models
- Brand reputation and reliability
- Typical sale/discount pricing patterns for this brand and model
- Kit pricing and how to prorate the tool's value within kits

# PRICING GUIDELINES
- Base your target price on standard sale/discount prices, not MSRP
- Only use list price if the tool never goes on sale or is never included in discounted kits
- Consider both standalone and kit proration scenarios
- Be objective and realistic in your evaluation
- This should be the best value typically available through any channel

# JSON SCHEMA
You must respond with exactly this JSON structure:
{{
  "component_sku": "string",
  "component_name": "string", 
  "fair_price": number,
  "reasoning": "string",
  "pros": ["string", "string", "string"],
  "cons": ["string", "string", "string"],
  "market_notes": "string"
}}

# COMPONENT DATA
SKU: {component_info['sku']}
Name: {component_info['name']}
Brand: {component_info['brand']}
Description: {component_info['description']}
Battery Platforms: {', '.join(component_info['battery_platforms'])}
Battery Voltages: {', '.join(component_info['battery_voltages'])}
Categories: {', '.join(component_info['item_categories'])}
Attributes: {json.dumps(component_attributes, indent=2)}

# CRITICAL REMINDERS
- This is a bare tool evaluation - assume the buyer already has batteries/chargers
- Provide a SINGLE fair_price value as a number, not a dictionary
- The reasoning should explain WHERE this target price comes from (kit deals vs standalone)
- Pros and cons should be arrays of strings, each item being a complete sentence
- Respond with ONLY the JSON object, no additional text
"""
        
        queried_components += 1
        try:
            response = model.generate_content(input_string)
            print(f"\nAnalyzing: {component_info['name']} ({component_info['sku']})")
            print(response.text)
            
            # Parse JSON response and add to component
            try:
                # Clean the response text by removing markdown code blocks
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]  # Remove ```json
                if response_text.startswith('```'):
                    response_text = response_text[3:]   # Remove ```
                if response_text.endswith('```'):
                    response_text = response_text[:-3]  # Remove trailing ```
                response_text = response_text.strip()
                
                analysis_data = json.loads(response_text)
                
                # Validate the response structure
                required_fields = ['component_sku', 'component_name', 'fair_price', 'reasoning', 'pros', 'cons', 'market_notes']
                missing_fields = [field for field in required_fields if field not in analysis_data]
                
                if missing_fields:
                    print(f"⚠️  Missing required fields for {component_info['sku']}: {missing_fields}")
                    analysis_data['validation_error'] = f"Missing fields: {', '.join(missing_fields)}"
                
                # Validate fair_price is a single number, not a dictionary
                if 'fair_price' in analysis_data:
                    if isinstance(analysis_data['fair_price'], dict):
                        print(f"⚠️  fair_price is a dictionary for {component_info['sku']}, extracting first value")
                        # Extract the first numeric value from the dictionary
                        for key, value in analysis_data['fair_price'].items():
                            if isinstance(value, (int, float)):
                                analysis_data['fair_price'] = value
                                analysis_data['original_fair_price_dict'] = analysis_data['fair_price']
                                break
                        else:
                            print(f"❌ No numeric value found in fair_price dictionary for {component_info['sku']}")
                            analysis_data['validation_error'] = "fair_price dictionary contains no numeric values"
                    elif not isinstance(analysis_data['fair_price'], (int, float)):
                        print(f"⚠️  fair_price is not a number for {component_info['sku']}: {type(analysis_data['fair_price'])}")
                        analysis_data['validation_error'] = f"fair_price is not a number: {type(analysis_data['fair_price'])}"
                
                component.fair_price_narrative = analysis_data
                component.save()
                print(f"✓ Saved analysis for {component_info['sku']}")
            except json.JSONDecodeError as json_error:
                print(f"JSON parsing error for {component_info['sku']}: {str(json_error)}")
                print(f"Raw response: {response.text[:200]}...")
                # Save raw response as text if JSON parsing fails
                component.fair_price_narrative = {"raw_response": response.text, "parse_error": str(json_error)}
                component.save()
                
        except Exception as e:
            print(f"Error analyzing {component_info['sku']}: {str(e)}")
        
        time.sleep(5)  # Rate limiting
    
    # Print summary statistics
    print(f"\n{'='*50}")
    print("📊 ANALYSIS SUMMARY")
    print(f"{'='*50}")
    print(f"Total components processed: {total_components}")
    print(f"Components skipped (already have data): {skipped_components}")
    print(f"Components queried with Gemini: {queried_components}")
    print(f"API calls saved: {skipped_components}")
    print(f"{'='*50}")
        
except ItemCategories.DoesNotExist:
    print("No 'drill driver' category found. Available categories:")
    for category in ItemCategories.objects.all()[:10]:  # Show first 10 categories
        print(f"- {category.name}")
except Exception as e:
    print(f"Error: {str(e)}")