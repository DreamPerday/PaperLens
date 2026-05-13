import urllib.request, json, re

resp = urllib.request.urlopen(
    'http://localhost:8000/api/projects/1384f10e-eeb7-493e-86cf-0d42e160f130/documents/3453db42-6086-4b12-a67d-eca0f7258926/content',
    timeout=60
)
data = json.loads(resp.read())
text = data['data']['original_text']

tables = len(re.findall(r'<table', text))
trs = len(re.findall(r'<tr[\s>]', text))
imgs = len(re.findall(r'<img', text))
display_math = len(re.findall(r'\$\$', text)) // 2
inline_math = len(re.findall(r'\$[^$]+\$', text))
headings = len(re.findall(r'^#{1,6}\s', text, re.MULTILINE))
html_divs = len(re.findall(r'<div', text))

print(f'Tables: {tables}, TRs: {trs}, Images: {imgs}, DIVs: {html_divs}')
print(f'Display math: {display_math}, Inline math: {inline_math}')
print(f'Markdown headings: {headings}')
print(f'Total chars: {len(text)}')

# Show some table content
for m in re.finditer(r'<table[\s\S]{0,200}', text):
    print(f'\nTable preview: {m.group()[:200]}')
    break

# Show tr content  
for m in re.finditer(r'<tr[\s\S]{0,200}', text):
    if '<td>' in m.group():
        print(f'\nTR preview: {m.group()[:200]}')
        break
