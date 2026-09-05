"""Rebuildable, anonymously labelled full-output view; never an approval."""
from __future__ import annotations

from html import escape
from pathlib import Path

from .benchmark import tree_files
from .refs import confined, digest, encoded, fail, read_json, sha


def render(manifest: dict, root: Path) -> dict:
    ledger_path=root/'ATTEMPTS.json';ledger_hash=sha(ledger_path);ledger=read_json(ledger_path)
    if ledger.get('finished') is not True or ledger.get('suite_sha256')!=digest(manifest):
        fail('BENCHMARK_INCOMPLETE','finish the fixed schedule before rendering its full-output view')
    runs=ledger['runs'];mapping={};bindings={};sections=[]
    targets=[confined(root,name) for name in ('QUALITY_REVIEW.html','QUALITY_MAPPING.json')]
    for key,run in runs.items():
        work=confined(root,run['work'])
        if any(p.is_relative_to(work) for p in targets):
            fail('INVALID_BENCHMARK','a derived report cannot overwrite a trial workspace')
        expected=run.get('final_files') or run.get('current_files')
        if expected is None or tree_files(work)!=expected:
            fail('BENCHMARK_MISMATCH','output changed before human-view rendering: '+key)
        bindings[key]=(work,expected)
    for case in manifest['cases']:
        for round_id in (1,2):
            pair=f"{case['id']}:{round_id}"
            variants=['old','new']
            if int(digest([pair,digest(runs)])[-1],16)%2:variants.reverse()
            mapping[pair]={};columns=[]
            for label,variant in zip(('A','B'),variants):
                key=f"{case['id']}:{variant}:{round_id}";run=runs[key];work,expected=bindings[key]
                mapping[pair][label]={'run':key,'files':expected}
                status='試次完成；作品品質仍須人類判斷' if run.get('technical_pass') else '試次未完成；不得視為同等品質通過'
                files=[]
                for name in case['outputs']:
                    path=confined(work,name)
                    if name not in expected:
                        files.append('<p class="missing">缺少必要產物：'+escape(name)+'</p>');continue
                    files.append('<details open><summary>'+escape(name)+'</summary><pre>'+escape(path.read_text())+'</pre></details>')
                columns.append('<article><h3>樣本 '+label+'</h3><p>'+status+'</p>'+''.join(files)+'</article>')
            requirements=case['task']+'\n\n'+'\n'.join(case['requirements'])
            authorities='\n\n'.join(name+'\n'+body for name,body in case['fixtures'].items())
            sections.append('<section><h2>'+escape(case['id'])+' — 第 '+str(round_id)+' 輪</h2>'
                '<details><summary>固定交付要求</summary><pre>'+escape(requirements)+'</pre></details>'
                '<details><summary>共同來源／限制</summary><pre>'+escape(authorities)+'</pre></details>'
                '<div class="pair">'+''.join(columns)+'</div></section>')
    document='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Factory 候選作品比較</title><style>
body{font:16px/1.6 system-ui;margin:2rem;background:#fafafa;color:#202124}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}article{min-width:0;background:white;padding:1rem;border:1px solid #bbb}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 ui-monospace,monospace;max-height:75vh;overflow:auto}
summary{cursor:pointer;font-weight:600}.missing{color:#9b1c1c}section{margin:3rem 0}h1{font-size:1.6rem}
@media(max-width:900px){body{margin:1rem}.pair{grid-template-columns:1fr}}
</style><h1>Factory 候選作品比較</h1>
<p>這是可重建的作品視圖，不是批准或驗收。完整文字未縮短，缺少產物會明列；未完成的試次不能當作同等品質通過。</p>
<p>樣本以 A/B 隱去流程標籤；文件自身可能透露流程特徵，並不保證無法推知來源。判斷前請勿開啟對照映射檔。</p>
<p>請檢查要求覆蓋、意圖／因果、人物知識與聲音、完整正文、語意／本地化及分支後果。本頁不提供一鍵批准。</p>'''
    document+='<p>來源紀錄 SHA-256：<code>'+ledger_hash+'</code></p>'+''.join(sections)+'</html>'
    if sha(ledger_path)!=ledger_hash or any(tree_files(work)!=expected for work,expected in bindings.values()):
        fail('CONCURRENT_WRITE','source changed while rendering the view')
    # These are derived views outside every trial worktree. No evidence, old
    # output, review verdict, acceptance or human-ruling object is rewritten.
    targets[0].write_text(document)
    targets[1].write_bytes(encoded({'schema_version':'factory_quality_view_mapping.v2',
        'ledger_sha256':ledger_hash,'suite_sha256':digest(manifest),'pairs':mapping}))
    return {'quality_view':str(targets[0]),'quality_mapping':str(targets[1]),'ledger_sha256':ledger_hash}
