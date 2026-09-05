"""Fixed-case Codex CLI benchmark and strict JSONL accounting; no model API runner."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from .refs import FactoryError, digest, encoded, exclusive_json, fail, read_json, sha

USAGE_SOURCE = "https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable"


def usage(path: Path) -> dict:
    result = dict(input_tokens=0, output_tokens=0, cached_input_tokens=0,
                  reasoning_output_tokens=0, tool_calls=0, failed_events=0, turns=0, complete=True)
    terminal = False
    seen_items = set()
    try:
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except (ValueError, OSError) as exc:
        fail("INVALID_USAGE", f"{path}: {exc}")
    for event in events:
        if not isinstance(event, dict):
            fail("INVALID_USAGE", "every JSONL event must be an object")
        typ = event.get("type")
        if typ == "turn.started":
            terminal = False
        if typ in ("turn.completed", "turn.failed"):
            terminal = True
            if typ == "turn.failed":
                result["failed_events"] += 1
            raw = event.get("usage")
            if not isinstance(raw, dict):
                result["complete"] = False
                continue
            for field in ("input_tokens", "output_tokens", "cached_input_tokens"):
                if type(raw.get(field)) is not int or raw[field] < 0:
                    fail("INVALID_USAGE", f"{path}: missing/invalid {field}")
            reasoning = raw.get("reasoning_output_tokens", 0)
            if type(reasoning) is not int or not 0 <= reasoning <= raw["output_tokens"]:
                fail("INVALID_USAGE", "reasoning must be a subset of output, not added twice")
            if raw["cached_input_tokens"] > raw["input_tokens"]:
                fail("INVALID_USAGE", "cached input exceeds total input")
            for field in ("input_tokens", "output_tokens", "cached_input_tokens"):
                result[field] += raw[field]
            result["reasoning_output_tokens"] += reasoning
            result["turns"] += 1
        if typ == "error":
            result["failed_events"] += 1
            result["complete"] = False
        item = event.get("item", {})
        if typ == "item.completed" and item.get("type") in ("command_execution", "file_change", "mcp_tool_call", "web_search", "collab_agent_tool_call"):
            key = item.get("id")
            if key not in seen_items:
                result["tool_calls"] += 1
                seen_items.add(key)
                if item.get("exit_code", 0) not in (0, None) or item.get("status") == "failed":
                    result["failed_events"] += 1
            if item.get("type") == "collab_agent_tool_call":
                # Main-thread JSONL does not prove child-session usage. The
                # benchmark harness launches reviewers separately instead.
                result["complete"] = False
    result["complete"] &= terminal and result["turns"] > 0
    result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    return result


def stages_for(case, variant):
    return case[variant + '_stages']


def source_bundle(manifest, factory):
    """Freeze all source bytes once before the first author session."""
    result={}
    for case in manifest['cases']:
        for variant in ('old','new'):
            values=[]
            for name in case['sources'][variant]:
                from .refs import confined
                if variant=='old':
                    body=subprocess.run(['git','-C',str(factory),'show',f"{manifest['baseline_revision']}:{name}"],
                        capture_output=True,text=True,check=True).stdout
                else: body=confined(factory,name).read_text()
                values.append({'path':name,'text':body})
            result[case['id']+':'+variant]=values
    return result


def tree_files(root):
    """Produced state, not engine caches or usage logs; no backup/snapshot bytes."""
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and not any(x in ('.git','.godot','__pycache__') for x in p.relative_to(root).parts)
            and not p.name.endswith(('.pyc','.import'))}


def authority_intact(case, work):
    mutable=set(case.get('mutable_fixtures',[]))
    if mutable-set(case['fixtures']):fail('INVALID_BENCHMARK','unknown mutable fixture')
    return all((work/name).is_file() and (work/name).read_text()==body
               for name,body in case['fixtures'].items() if name not in mutable)


def design_files(case, work):
    return {name:sha(work/name) for name in case.get('design_outputs',[]) if (work/name).is_file()}


def summarize(manifest, root, human_quality=None):
    from .refs import confined
    attempts_path=root/'ATTEMPTS.json'
    if not attempts_path.exists():
        return {'status':'BENCHMARK_NOT_RUN','accepted':False,'usage_source':USAGE_SOURCE}
    ledger=read_json(attempts_path)
    if ledger.get('suite_sha256')!=digest(manifest): fail('BENCHMARK_MISMATCH','suite/settings/fixtures changed')
    cases={c['id']:c for c in manifest['cases']}
    expected_keys={(c,v,r) for c in cases for v in ('old','new') for r in (1,2)}
    expected_sources=ledger.get('source_digests',{})
    if set(expected_sources)!={c+':'+v for c in cases for v in ('old','new')}:
        fail('BENCHMARK_MISMATCH','missing frozen source membership')
    execution_issues=ledger.get('execution_issues',[])
    totals={};seen=set();all_complete=ledger.get('finished') is True and not execution_issues
    for a in ledger['attempts']:
        key=(a['case'],a['variant'],a['round'])
        if key not in expected_keys: fail('INVALID_BENCHMARK','unmatched attempt would hide cost')
        case=cases[a['case']];stages=stages_for(case,a['variant'])
        if type(a['stage_index']) is not int or not 0<=a['stage_index']<len(stages):
            fail('INVALID_BENCHMARK','unknown stage')
        if a['kind'] not in ('stage','rework') or (a['kind']=='stage' and a['role']!=stages[a['stage_index']]['role']):
            fail('INVALID_BENCHMARK','unknown stage/role accounting')
        if (a['fixture_digest']!=digest(case['fixtures']) or a['source_digest']!=expected_sources[a['case']+':'+a['variant']]
                or a['settings_digest']!=digest({k:manifest[k] for k in ('model','reasoning','permissions')})):
            fail('BENCHMARK_MISMATCH','source/fixture/settings changed across attempts')
        name=a['jsonl'];path=confined(root,name)
        if name in seen or sha(path)!=a['sha256']:fail('INVALID_BENCHMARK','duplicate or changed usage log')
        seen.add(name);u=usage(path);all_complete &= u['complete']
        total=totals.setdefault(key,{k:0 for k in ('total_tokens','input_tokens','output_tokens','cached_input_tokens','reasoning_output_tokens','tool_calls','failed_events','attempts','rework_attempts')})
        total['metering_complete']=total.get('metering_complete',True) and u['complete']
        for k in ('total_tokens','input_tokens','output_tokens','cached_input_tokens','reasoning_output_tokens','tool_calls','failed_events'):total[k]+=u[k]
        total['attempts']+=1;total['rework_attempts']+=a['kind']=='rework'
    runs=ledger.get('runs',{})
    if set(runs)-{f'{c}:{v}:{r}' for c,v,r in expected_keys}:fail('INVALID_BENCHMARK','unknown output group')
    for c,v,r in expected_keys:
        run=runs.get(f'{c}:{v}:{r}')
        if not run or run.get('completed_stages')!=list(range(len(stages_for(cases[c],v)))) or run.get('technical_pass') is not True:
            all_complete=False;continue
        work=confined(root,run['work'])
        if not authority_intact(cases[c],work):fail('BENCHMARK_MISMATCH','immutable fixture authority changed')
        if run.get('sealed_design',{}) != design_files(cases[c],work):fail('BENCHMARK_MISMATCH','reviewed design changed after its boundary')
        if tree_files(work)!=run['final_files']: fail('BENCHMARK_MISMATCH','quality-reviewed outputs changed')
        if any(name not in run['final_files'] for name in cases[c]['outputs']):all_complete=False
        for role in cases[c].get('design_review_roles',{}).get(v,[]):
            reviews=[a for a in ledger['attempts'] if (a['case'],a['variant'],a['round'])==(c,v,r) and a['role']==role and a['kind']=='stage']
            if not reviews or reviews[-1].get('verdict')!='PASS' or reviews[-1].get('design_input')!=run.get('sealed_design'):
                fail('BENCHMARK_MISMATCH','final design is not the version passed by every design reviewer')
        # A completion entry is supported only by a successful model/semantic
        # stage attempt, not merely a process exit or self-authored run summary.
        for i in run['completed_stages']:
            matches=[a for a in ledger['attempts'] if (a['case'],a['variant'],a['round'])==(c,v,r)
                     and a['stage_index']==i and a['kind']=='stage']
            if not matches or matches[-1].get('verdict')!='PASS' or matches[-1]['returncode']!=0:all_complete=False
    # Reject orphan logs too: a crash cannot make a costly session disappear.
    if {p.name for p in root.glob('*.jsonl')}!=seen:fail('INVALID_BENCHMARK','unaccounted JSONL session')
    comparisons=[]
    for c in cases:
        for r in (1,2):
            old=totals.get((c,'old',r));new=totals.get((c,'new',r))
            known_lower=bool(old and new and new['total_tokens']<old['total_tokens'])
            comparisons.append({'case':c,'round':r,'old':old,'new':new,'known_lower':known_lower,
                'lower':bool(known_lower and old['metering_complete'] and new['metering_complete'])})
    action='CONFIRM_EQUAL_QUALITY '+digest(manifest)+' '+digest(runs)
    quality_ok=False
    if human_quality:
        source=human_quality.get('source',{})
        if isinstance(source,dict) and set(source)=={'path','sha256'}:
            source_path=confined(root,source['path'])
            raw=read_json(source_path) if source_path.is_file() and sha(source_path)==source['sha256'] else {}
            quality_ok=bool(human_quality.get('owner')=='USER' and
                human_quality.get('suite_sha256')==digest(manifest) and human_quality.get('attempts_sha256')==sha(attempts_path) and
                human_quality.get('outputs_sha256')==digest(runs) and human_quality.get('equal_quality') is True and
                set(human_quality.get('passed_cases',[]))==set(cases) and human_quality.get('raw_verdict_quote')==action and
                raw.get('role')=='user' and raw.get('content','').strip()==action)
    passed=bool(all_complete and quality_ok and all(c['lower'] for c in comparisons))
    return {'status':'BENCHMARK_PASSED' if passed else 'BENCHMARK_INCOMPLETE' if not all_complete else
            'HUMAN_QUALITY_REVIEW_REQUIRED' if not quality_ok else 'TOKEN_TARGET_NOT_MET',
            'accepted':passed,'comparisons':comparisons,'usage_complete':bool(all_complete),
            'human_quality_confirmed':quality_ok,'usage_source':USAGE_SOURCE,
            'execution_issues':execution_issues,
            'stopped_runs':{k:v['stopped_reason'] for k,v in runs.items() if v.get('stopped_reason')},
            'mechanical_failures':len(ledger.get('mechanical_events',[])),
            'all_attempt_tokens':sum(t['total_tokens'] for t in totals.values()),
            'human_quality_action':action if ledger.get('finished') else None}


def response(log):
    events=[json.loads(s) for s in log.read_text().splitlines() if s.strip()]
    session=next((e.get('thread_id') for e in events if e.get('type')=='thread.started'),None)
    messages=[e.get('item',{}).get('text','') for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
    try:
        raw=messages[-1].strip();raw=raw.removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        result=json.loads(raw)
        if result.get('verdict') not in ('PASS','FAIL','BLOCKED') or not isinstance(result.get('findings'),list):raise ValueError()
    except (IndexError,ValueError,AttributeError):result={'verdict':'BLOCKED','findings':['Missing structured stage result.']}
    return session,result


def technical_check(case,work):
    """Same output checks in both variants, independent of author claims."""
    if any(not (work/p).is_file() for p in case['outputs']):return False
    if case['id']=='authorized_repair':
        # Actual Godot execution against the produced implementation, not grep.
        runner=work/'factory_regression.gd'
        runner.write_text('extends SceneTree\nfunc _init():\n    var d = load("res://depot.gd").new()\n    for expected in [2, 1, 0, 0]:\n        if d.dispatch() != expected:\n            quit(1)\n            return\n    print("FACTORY_REGRESSION_PASS")\n    quit(0)\n')
        if not (work/'project.godot').exists():(work/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Factory isolated regression"\n')
        p=subprocess.run(['godot','--headless','--path',str(work),'--script',str(runner)],capture_output=True,text=True,timeout=60)
        (work/'FACTORY_TECHNICAL.log').write_text(p.stdout+p.stderr)
        return p.returncode==0 and 'FACTORY_REGRESSION_PASS' in p.stdout
    if case['id']=='chapter_production':
        try:
            en=read_json(work/'en.json');zh=read_json(work/'zh_TW.json')
            if set(en)!=set(zh) or not en or any(not isinstance(v,str) or not v.strip() for v in [*en.values(),*zh.values()]):return False
            raw=json.loads((work/'scenes.json').read_text());nodes=raw if isinstance(raw,list) else raw.get('nodes',raw.get('scenes'))
            if isinstance(nodes,dict):nodes=[{'id':k,**v} for k,v in nodes.items()]
            if not isinstance(nodes,list) or not nodes:return False
            ids={n['id'] for n in nodes}
            if len(ids)!=len(nodes):return False
            for n in nodes:
                if n.get('text_key') and n['text_key'] not in en:return False
                for edge in [n.get('next'),*[x.get('next') for x in n.get('choices',[])]]:
                    if edge and edge not in ids:return False
            (work/'FACTORY_TECHNICAL.log').write_text('PASS: identical nonempty locale keys; unique nodes; all text/route references resolve. Semantic quality remains human-owned.\n')
        except (KeyError,TypeError,ValueError):return False
    return True


def run(manifest,factory,output,resume=False):
    """Finite CLI workflow trials; all failures/retries retained, no API daemon.

    Fresh reviewers never share reports. New author stages resume one Codex
    thread. A clean-room session receives only the actual sanitized packet in
    an independently initialized directory, never a copied game repository.
    """
    from .refs import confined
    if output.exists() and any(output.iterdir()) and not resume:fail('BENCHMARK_OUTPUT_EXISTS','use --resume for the exact existing ledger or an empty isolated test directory')
    if output.resolve().is_relative_to(factory.resolve()):fail('INVALID_BENCHMARK','outputs must stay outside Factory')
    if manifest['model']!='gpt-6-astra' or manifest['rounds']!=2:fail('INVALID_BENCHMARK','Astra and two matched rounds required')
    bundles=source_bundle(manifest,factory)
    output.mkdir(parents=True,exist_ok=True)
    settings=digest({k:manifest[k] for k in ('model','reasoning','permissions')})
    if resume:
        ledger=read_json(output/'ATTEMPTS.json')
        if ledger['suite_sha256']!=digest(manifest) or ledger['source_digests']!={k:digest(v) for k,v in bundles.items()}:
            fail('BENCHMARK_MISMATCH','cannot resume changed suite or sources')
        summarize(manifest,output)  # validates every prior usage/output binding
        if ledger.get('finished'):return summarize(manifest,output)
    else:
        ledger={'schema_version':'factory_benchmark_attempts.v2','suite_sha256':digest(manifest),'finished':False,
                'source_digests':{k:digest(v) for k,v in bundles.items()},'attempts':[],'runs':{}}
    def save():(output/'ATTEMPTS.json').write_bytes(encoded(ledger))
    save()
    for case in manifest['cases']:
      for round_id in (1,2):
       for variant in ('old','new'):
        name=f"{case['id']}-{round_id}-{variant}";work=output/name
        key=f"{case['id']}:{variant}:{round_id}"
        stages=stages_for(case,variant);author_session=None;language_results=[]
        run_record=ledger['runs'].get(key)
        previous_attempts=[a for a in ledger['attempts'] if (a['case'],a['variant'],a['round'])==(case['id'],variant,round_id)]
        if run_record:
            if run_record.get('technical_pass') and run_record['completed_stages']==list(range(len(stages))):continue
            current=tree_files(work)
            expected=run_record.get('current_files')
            if expected is not None:
                if current!=expected:fail('BENCHMARK_MISMATCH','interrupted fixture changed outside its checkpoint')
            elif not previous_attempts or previous_attempts[-1].get('input_files_sha256')!=digest(current):
                fail('BENCHMARK_MISMATCH','legacy interrupted run has no supported exact checkpoint')
            if run_record.get('stopped_reason'):continue
            if (run_record.get('repair_rounds',0)>=manifest['max_rework_rounds'] and previous_attempts
                    and previous_attempts[-1]['verdict']!='PASS'):
                run_record['stopped_reason']='REWORK_LIMIT';save();continue
            # Reviewer/clean-room reports remain isolated outside the worktree.
            # Only the continuing author's own thread resumes.
            if variant=='new':
                author_session=next((a.get('session_id') for a in previous_attempts if a['role'].startswith('author') and a.get('session_id')),None)
            language_results=run_record.get('language_results',[])
        else:
            work.mkdir();subprocess.run(['git','init','-q','-b','main',str(work)],check=True)
            for path,body in case['fixtures'].items():
                dest=confined(work,path);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(body)
            run_record={'work':name,'completed_stages':[],'technical_pass':False,'final_files':{},'sealed_design':{},
                        'current_files':tree_files(work),'repair_rounds':0,'language_results':[]}
            ledger['runs'][key]=run_record
        sources=bundles[case['id']+':'+variant]
        def invoke(stage,index,kind='stage',feedback=None):
            nonlocal author_session
            ordinal=len(ledger['attempts']);log_name=f'{name}-{ordinal:04d}.jsonl';log=output/log_name
            if not authority_intact(case,work):fail('BENCHMARK_MISMATCH','author changed immutable fixture authority')
            stage_kind=stage['kind'];cwd=work;source_text='\n'.join('SOURCE '+x['path']+'\n'+x['text'] for x in sources)
            if stage_kind=='cleanroom':
                from story.v2 import validate_fluency_packet, FLUENCY_PACKET_CONTRACT
                packet_path=work/f"FLUENCY_{stage['locale']}.json"
                try:packet=validate_fluency_packet(read_json(packet_path),stage['locale'])
                except (FactoryError,OSError,ValueError) as exc:
                    # No model has been invoked and no blind context received
                    # malformed content. Record the mechanical failure, then
                    # use the same bounded author-repair path as other gates.
                    finding=str(exc)+' '+FLUENCY_PACKET_CONTRACT
                    ledger.setdefault('mechanical_events',[]).append(dict(case=case['id'],round=round_id,variant=variant,
                        role=stage['role'],stage_index=index,code='INVALID_CLEANROOM_PACKET',finding=finding,
                        packet_sha256=sha(packet_path) if packet_path.is_file() else None,harness_sha256=sha(Path(__file__))))
                    save();return 2,{'verdict':'FAIL','findings':[finding]}
                cwd=output/f'cleanroom-{ordinal:04d}';cwd.mkdir()
                subprocess.run(['git','init','-q','-b','main',str(cwd)],check=True)
                source_text='SANITIZED SPOKEN-FLUENCY PACKET\n'+json.dumps(packet,ensure_ascii=False)
                task=stage['task'];requirements='Do not read other files, design, canon, peer reports or sibling paths.'
            else:
                task=case['task'];requirements='\n'.join(case['requirements'])
            prompt=('Isolated fixed Factory benchmark, never Banner. No delegation, web/provider access, credential access, edits outside this fixture or backup copies. '
                    'This harness owns all independent contexts and their usage. Reviewers must not read peer conclusions; report findings without editing. '
                    'Follow only CURRENT STAGE: do not perform later production early. Final response MUST be JSON with verdict PASS/FAIL/BLOCKED and findings array of strings. '
                    'PASS means this stage is satisfied, never USER/gameplay acceptance. Include complete polished lines in cleanroom findings.\n'+source_text+
                    '\nTASK\n'+task+'\nREQUIREMENTS\n'+requirements+'\nCURRENT STAGE\n'+stage['task'])
            if feedback:prompt+='\nREPAIR/INTEGRATION INPUT\n'+json.dumps(feedback,ensure_ascii=False)
            before=tree_files(work)
            design_input=design_files(case,work)
            # exec resume does not inherit exec's sandbox default from the
            # original invocation. Put the same root/options before the
            # subcommand, or a continuing author silently becomes read-only.
            common=['codex','exec','--ignore-user-config','--json','--model',manifest['model'],'-c',f'model_reasoning_effort="{manifest["reasoning"]}"',
                    '--sandbox',manifest['permissions'],'-C',str(cwd)]
            continuing=stage_kind=='author' and variant=='new' and author_session
            if continuing:
                prompt=('Continue the same fixed benchmark and full authorities already read. Do not repeat or shorten prior full deliverables. '
                        'Do only this stage; final response JSON verdict and findings. CURRENT STAGE: '+stage['task'])
                if feedback:prompt+='\nREPAIR/INTEGRATION INPUT\n'+json.dumps(feedback,ensure_ascii=False)
                command=common+['resume',author_session,prompt]
            else:command=common+[prompt]
            if stage['role']=='author_packets':
                from story.v2 import FLUENCY_PACKET_CONTRACT
                command[-1]+='\n'+FLUENCY_PACKET_CONTRACT
            with log.open('wb') as out,(output/(log_name+'.stderr')).open('wb') as err:
                try:code=subprocess.run(command,stdout=out,stderr=err,cwd=cwd,timeout=manifest['session_timeout_seconds']).returncode
                except subprocess.TimeoutExpired:code=124
            sid,result=response(log)
            if stage_kind=='author' and variant=='new' and not author_session:author_session=sid
            if stage_kind in ('review','cleanroom') and tree_files(work)!=before:
                result={'verdict':'BLOCKED','findings':['Independent reviewer illegally changed the candidate.']}
            ledger['attempts'].append(dict(case=case['id'],round=round_id,variant=variant,role=stage['role'],stage_index=index,
                kind=kind,jsonl=log_name,sha256=sha(log),returncode=code,verdict=result['verdict'],
                harness_sha256=sha(Path(__file__)),
                source_digest=digest(sources),fixture_digest=digest(case['fixtures']),settings_digest=settings,
                input_files_sha256=digest(before),design_input=design_input,session_id=sid))
            run_record['current_files']=tree_files(work)
            save()
            if not authority_intact(case,work):fail('BENCHMARK_MISMATCH','author changed immutable fixture authority; cost retained')
            return code,result
        index=len(run_record['completed_stages'])
        if run_record['completed_stages']!=list(range(index)):fail('INVALID_BENCHMARK','interrupted stage prefix is broken')
        total_repairs=run_record.get('repair_rounds',0)
        # The approved design is immutable across production. Narrative repair
        # revisits its real language dependencies rather than retaining stale
        # clean-room PASS records. Completed stage indices are evidence, not
        # irrevocable counters.
        narrative=any(s['kind']=='cleanroom' for s in stages)
        packet_index=next((i for i,s in enumerate(stages) if s['role']=='author_packets'),0)
        design_review_index=next((i for i,s in enumerate(stages) if s['kind']=='review'),0)
        while index<len(stages):
            stage=stages[index]
            end=index+1
            if stage['kind']=='review':
                while end<len(stages) and stages[end]['kind']=='review':end+=1
            # Whole independent boundary reruns after any candidate repair.
            retries=0
            while True:
                results=[]
                for stage_index in range(index,end):
                    current=stages[stage_index]
                    feedback=language_results if current['role']=='author_integrate' else None
                    code,result=invoke(current,stage_index,feedback=feedback)
                    results.append((code,result))
                if all(code==0 and result['verdict']=='PASS' for code,result in results):break
                if total_repairs>=manifest['max_rework_rounds']:
                    run_record['stopped_reason']='REWORK_LIMIT';break
                if any(not usage(output/a['jsonl'])['complete'] for a in ledger['attempts'][-len(results):]):return summarize(manifest,output)
                retries+=1;total_repairs+=1;run_record['repair_rounds']=total_repairs
                repair={'role':'author_rework','kind':'author','task':'Repair this failed boundary within the same approved scope. Preserve every full deliverable. The entire affected independent boundary will rerun.'}
                repair_code,repair_result=invoke(repair,index,'rework',[r for _,r in results])
                if repair_code or repair_result['verdict']!='PASS':
                    if total_repairs>=manifest['max_rework_rounds']:
                        run_record['stopped_reason']='REWORK_LIMIT';break
                if narrative and index>=packet_index:
                    # A narrative repair may touch spoken output; conservatively
                    # rerun extraction, clean-room, integration, canon and every
                    # affected design review before later output QA.
                    restart=min(packet_index,design_review_index) if variant=='old' else packet_index
                    run_record['completed_stages']=list(range(restart))
                    run_record['sealed_design']={};language_results=[]
                    index=restart;results=None
                    break
            if run_record.get('stopped_reason'):break
            if results is None:
                save();continue
            if run_record['sealed_design'] and design_files(case,work)!=run_record['sealed_design']:
                if total_repairs>=manifest['max_rework_rounds']:
                    run_record['stopped_reason']='REWORK_LIMIT';break
                total_repairs+=1;run_record['repair_rounds']=total_repairs
                restart=packet_index if narrative and variant=='new' else design_review_index
                run_record['completed_stages']=list(range(restart));run_record['sealed_design']={};language_results=[]
                index=restart;save();continue
            if any(stages[i]['role']=='completeness_project' for i in range(index,end)) or end==len(stages):
                run_record['sealed_design']=design_files(case,work)
            if stage['kind']=='cleanroom':language_results.append({'locale':stage['locale'],'result':results[0][1]})
            run_record['completed_stages'].extend(range(index,end));run_record['language_results']=language_results;save()
            index=end
        if not run_record.get('stopped_reason'):
            run_record['technical_pass']=technical_check(case,work)
            if not run_record['technical_pass']:run_record['stopped_reason']='TECHNICAL_CHECK_FAILED'
        run_record['final_files']=tree_files(work);save()
    ledger['finished']=True;save()
    return summarize(manifest,output)
