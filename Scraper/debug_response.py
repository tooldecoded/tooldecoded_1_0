import requests
import json
from pprint import pprint

# Set your Oxylabs API Credentials
username = "tooldecoded_c7GJz"
password = "5gM_3jpR=afdFAb"

# Structure payload
payload = {
    'source': 'universal',
    'url': 'https://www.homedepot.com/b/Tools-Power-Tools-Drills-Hammer-Drills/Milwaukee/Milwaukee-M18/N-5yc1vZc8wtZzvZ1z17rdr',
}

# Get response
response = requests.request(
    'POST',
    'https://realtime.oxylabs.io/v1/queries',
    auth=(username, password),
    json=payload,
)

print(f"Status Code: {response.status_code}")
print(f"Response Headers: {response.headers}")
print(f"Response Text Length: {len(response.text)}")

if response.status_code == 200:
    try:
        data = response.json()
        print("\n=== RESPONSE STRUCTURE ===")
        print(f"Response keys: {list(data.keys())}")
        
        if 'results' in data:
            print(f"Number of results: {len(data['results'])}")
            
            for i, result in enumerate(data['results']):
                print(f"\nResult {i}:")
                print(f"  Keys: {list(result.keys())}")
                print(f"  Status code: {result.get('status_code', 'N/A')}")
                print(f"  Type: {result.get('type', 'N/A')}")
                print(f"  Content length: {len(result.get('content', ''))}")
                print(f"  Content preview: {result.get('content', '')[:200]}...")
                
                # Check if there's any content
                content = result.get('content', '')
                if content:
                    print(f"  Content type: {type(content)}")
                    if isinstance(content, str):
                        print(f"  Content starts with: {content[:100]}")
                    else:
                        print(f"  Content: {content}")
                else:
                    print("  No content found")
        
        # Save full response for inspection
        with open('full_response.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("\nFull response saved to full_response.json")
        
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print("Raw response:")
        print(response.text[:1000])
else:
    print(f"Request failed with status code: {response.status_code}")
    print("Raw response:")
    print(response.text[:1000])
