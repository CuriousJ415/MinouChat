import requests

BASE_URL = 'http://localhost:8080/api/characters/test-update-character'

# Test 1: Missing 'name' field
payload_missing_name = {
    'id': 'default-anna',
    'role': 'life_coach',
    'personality': 'helpful'
}
response1 = requests.post(BASE_URL, json=payload_missing_name)
print('Test 1: Missing name field')
print('Status code:', response1.status_code)
print('Response:', response1.json())
print('-' * 40)

# Test 2: All required fields present
payload_all_fields = {
    'id': 'default-anna',
    'name': 'Anna',
    'role': 'life_coach',
    'personality': 'helpful',
    'system_prompt': 'You are Anna, a helpful life coach.',
    'model': 'mistral',
    'llm_provider': 'ollama'
}
response2 = requests.post(BASE_URL, json=payload_all_fields)
print('Test 2: All required fields present')
print('Status code:', response2.status_code)
print('Response:', response2.json()) 