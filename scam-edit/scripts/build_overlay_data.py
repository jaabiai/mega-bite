import json, re, glob, os
B='/tmp/claude-0/-home-user-mega-bite/cb57231b-dd93-57eb-a395-6963bf912552/scratchpad/'
icons={}
for f in glob.glob(B+'overlay/node_modules/lucide-static/icons/*.svg'):
    n=os.path.basename(f)[:-4]
    s=open(f).read()
    s=re.sub(r'<!--.*?-->','',s,flags=re.S).strip()
    m=re.match(r'<svg[^>]*>',s,flags=re.S)
    root=re.sub(r'\s+(class|width|height|stroke-width|fill|stroke|stroke-linecap|stroke-linejoin)="[^"]*"','',m.group(0))
    s=root+s[m.end():]
    icons[n]=re.sub(r'\s+',' ',s)
caps=json.load(open(B+'overlay/captions.json'))
open(B+'overlay/data.js','w').write('window.DATA='+json.dumps(dict(icons=icons,captions=caps),ensure_ascii=False)+';')
print(len(icons),'icons;',len(caps),'caption groups')
