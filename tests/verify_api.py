import urllib.request
import json

def verify():
    print("Testing GET /api/locations...")
    try:
        locs_resp = urllib.request.urlopen("http://127.0.0.1:5000/api/locations")
        locs = json.loads(locs_resp.read().decode())
        print(f"Success: {len(locs)} locations loaded. Sample: {locs[:5]}")
    except Exception as e:
        print(f"Failed to fetch locations: {e}")
        return

    print("Testing POST /api/recommend...")
    try:
        payload = {
            "location": "Btm",
            "budget": "low",
            "cuisine": "Burgers",
            "min_rating": 4.0,
            "additional_context": "quick bite"
        }
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            "http://127.0.0.1:5000/api/recommend",
            data=req_data,
            headers={'Content-Type': 'application/json'}
        )
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as he:
            if he.code == 400:
                res_body = json.loads(he.read().decode())
                print(f"Success (Expected 400 for over-constrained): {res_body['error']}")
                print(f"Suggestions: {res_body['suggestions']}")
            else:
                raise he

        print("Testing POST /api/recommend with relaxed criteria...")
        relaxed_payload = {
            "location": "Btm",
            "budget": "medium",
            "min_rating": 3.5,
            "additional_context": "nice seating"
        }
        req_data_rel = json.dumps(relaxed_payload).encode('utf-8')
        req_rel = urllib.request.Request(
            "http://127.0.0.1:5000/api/recommend",
            data=req_data_rel,
            headers={'Content-Type': 'application/json'}
        )
        recs_resp = urllib.request.urlopen(req_rel)
        recs = json.loads(recs_resp.read().decode())
        print(f"Success: Received {len(recs['recommendations'])} recommendations.")
        print(f"Fallback Active: {recs['fallback']}")
        print(f"Summary: {recs['summary']}")
        
        if recs['recommendations']:
            first = recs['recommendations'][0]
            print(f"Sample Rec - Name: {first['name']}, Location: {first['location']}, Cuisines: {first['cuisines']}, Rating: {first['rating']}, Explanation: {first['explanation']}")
    except Exception as e:
        print(f"Verification failed: {e}")


if __name__ == "__main__":
    verify()
