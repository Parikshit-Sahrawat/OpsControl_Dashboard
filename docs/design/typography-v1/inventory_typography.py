"""Read-only literal typography inventory at an immutable Git source."""
import argparse, collections, json, re, subprocess
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--source',default='54f26e51106469e285dd747dd6b8afd09ca43ce6');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
root=Path(__file__).resolve().parents[3]
def git(*values):return subprocess.check_output(['git',*values],cwd=root,text=True)
paths=git('ls-tree','-r','--name-only',args.source,'frontend/src','frontend/index.html').splitlines();records=[];loading=[]
for file in paths:
    if not file.endswith(('.css','.jsx','.js','.html')):continue
    text=git('show',args.source+':'+file)
    for match in re.finditer(r'(?<![-\w])(font(?:-family|-size|-weight|-style|-variant-numeric)?|line-height|letter-spacing)\s*:\s*([^;}]+)',text):
        start=match.start();left=text.rfind('{',0,start);selector=text[max(0,text.rfind('}',0,left)+1):left].strip()[-160:]
        records.append(dict(file=file,line=text.count('\n',0,start)+1,offset=start,selector_or_context=selector,property=match.group(1),value=match.group(2).strip(),kind='CSS_OR_STYLE_TEXT'))
    for match in re.finditer(r'\b(fontFamily|fontSize|fontWeight|lineHeight|letterSpacing)\s*:\s*([^,}\n]+)',text):
        records.append(dict(file=file,line=text.count('\n',0,match.start())+1,offset=match.start(),selector_or_context=text[max(0,match.start()-45):match.start()].strip(),property=match.group(1),value=match.group(2).strip(),kind='REACT_INLINE'))
    if re.search(r'@font-face|fonts\.googleapis|fonts\.gstatic|\.(?:woff2?|ttf|otf)["\x27)]',text):loading.append(file)
args.output.write_text(json.dumps({'source_sha':args.source,'method':'Literal declaration inventory with byte offsets; CSS cascade/inheritance evaluated separately in browser. CSS shorthand included; dynamic expressions retained, not inferred.','declarations':records,'counts_by_property':dict(collections.Counter(r['property'] for r in records)),'loading_source_matches':loading,'font_binary_paths':[p for p in paths if p.endswith(('.woff','.woff2','.ttf','.otf'))]},indent=2)+'\n')
