import requests, json

url = 'https://api.uxcodedev.com.br'
login = requests.post(f'{url}/auth/login', data={'username':'admin@andreja.com','password':'admin123'}, timeout=10)
token = login.json().get('access_token','')
headers = {'Authorization': f'Bearer {token}'}

r = requests.get(f'{url}/admin/brands', headers=headers, timeout=10)
brands = r.json()
otis = [b for b in brands if 'otis' in b.get('name','').lower() and 'lg' not in b.get('name','').lower()]

if otis:
    bid = otis[0]['id']
    print(f"Brand: {otis[0]['name']} (id={bid}, slug={otis[0].get('slug','')})")
    docs = requests.get(f'{url}/admin/brands/{bid}/documents', headers=headers, timeout=10)
    doc_list = docs.json()
    print(f"\n=== OTIS DOCUMENTS ON VPS ({len(doc_list)} total) ===\n")
    for d in doc_list:
        status = d.get('status','?')
        tp = d.get('total_pages', 0)
        pp = d.get('processed_pages', 0)
        fn = d.get('original_filename','?')
        did = d.get('id','?')
        print(f"  [{status:>10}] ID={did:>3} | {fn:<55} | pages: {pp}/{tp}")
else:
    print("No Otis brand found")
