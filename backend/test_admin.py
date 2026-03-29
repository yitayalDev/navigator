"""Test admin routes"""
from server import app

client = app.test_client()

# Test admin/login
print('Testing /admin/login...')
response = client.get('/admin/login')
print(f'Status: {response.status_code}')
print(f'Data length: {len(response.data)}')
if response.status_code == 200:
    print('SUCCESS! Login page loads correctly')
elif response.status_code == 500:
    print('500 Error detected')
    # Try to get error details
    print(f'First 1000 chars: {response.data[:1000]}')