import urllib.request
import urllib.error
import json

print('RUNNING')
url = 'http://localhost:8000/health'
try:
    with urllib.request.urlopen(url, timeout=5) as r:
        print('HEALTH', r.status, r.read().decode())
except Exception as e:
    print('HEALTH_FAIL', type(e).__name__, e)

url = 'http://localhost:8000/step'
data = json.dumps({'action': {'action_type': 'inspect', 'component_id': 'top_chord_1'}}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('STEP', r.status, r.read().decode())
except urllib.error.HTTPError as e:
    print('STEP_HTTP', e.code)
    try:
        print(e.read().decode())
    except Exception as e2:
        print('READ_ERR', e2)
except Exception as e:
    print('STEP_FAIL', type(e).__name__, e)
