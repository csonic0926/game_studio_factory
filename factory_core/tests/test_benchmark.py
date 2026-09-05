import json
from pathlib import Path
import tempfile
import unittest
from factory_core import benchmark
from factory_core.refs import FactoryError,digest,encoded,sha

class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.suite={'model':'gpt-6-astra','reasoning':'high','permissions':'workspace-write',
           'cases':[{'id':'one','fixtures':{'SOURCE.md':'same'},'outputs':['OUT.md'],
                     'old_stages':[{'role':'author','kind':'author'}], 'new_stages':[{'role':'author','kind':'author'}]}]}
        self.ledger={'suite_sha256':digest(self.suite),'finished':True,'source_digests':{'one:old':'a','one:new':'b'},'attempts':[],'runs':{}}
        for variant in ('old','new'):
            for r in (1,2):
                name=f'{variant}{r}.jsonl';path=self.root/name
                path.write_text(json.dumps({'type':'turn.completed','usage':{'input_tokens':100 if variant=='old' else 50,'cached_input_tokens':20,'output_tokens':10,'reasoning_output_tokens':5}})+'\n')
                self.ledger['attempts'].append(dict(case='one',variant=variant,round=r,stage_index=0,kind='stage',role='author',
                    fixture_digest=digest(self.suite['cases'][0]['fixtures']),source_digest=self.ledger['source_digests']['one:'+variant],
                    settings_digest=digest({k:self.suite[k] for k in ('model','reasoning','permissions')}),
                    jsonl=name,sha256=sha(path),returncode=0,verdict='PASS'))
                work=self.root/f'{variant}{r}';work.mkdir();(work/'OUT.md').write_text('full output');(work/'SOURCE.md').write_text('same')
                self.ledger['runs'][f'one:{variant}:{r}']=dict(work=work.name,completed_stages=[0],technical_pass=True,final_files=benchmark.tree_files(work))
        self.save()

    def save(self):
        (self.root/'ATTEMPTS.json').write_bytes(encoded(self.ledger))
        action='CONFIRM_EQUAL_QUALITY '+digest(self.suite)+' '+digest(self.ledger['runs'])
        raw=self.root/'quality-user.json';raw.write_bytes(encoded({'role':'user','content':action}))
        self.quality=dict(owner='USER',suite_sha256=digest(self.suite),attempts_sha256=sha(self.root/'ATTEMPTS.json'),outputs_sha256=digest(self.ledger['runs']),equal_quality=True,passed_cases=['one'],raw_verdict_quote=action,source={'path':raw.name,'sha256':sha(raw)})

    def test_total_reasoning_cached_not_double_counted(self):
        u=benchmark.usage(self.root/'old1.jsonl');self.assertEqual(u['total_tokens'],110);self.assertEqual(u['cached_input_tokens'],20)
        self.assertEqual(benchmark.summarize(self.suite,self.root,self.quality)['status'],'BENCHMARK_PASSED')

    def test_missing_human_quality_is_never_savings_acceptance(self):
        self.assertEqual(benchmark.summarize(self.suite,self.root)['status'],'HUMAN_QUALITY_REVIEW_REQUIRED')

    def test_execution_protocol_deviation_cannot_be_accepted(self):
        self.ledger['execution_issues']=[{'code':'RESUME_SANDBOX_MISMATCH','attempts':['new1.jsonl']}]
        self.save()
        result=benchmark.summarize(self.suite,self.root,self.quality)
        self.assertEqual(result['status'],'BENCHMARK_INCOMPLETE')
        self.assertFalse(result['accepted'])
        self.assertEqual(result['execution_issues'],self.ledger['execution_issues'])

    def test_user_rejection_cannot_confirm_equal_quality(self):
        raw=self.root/'quality-user.json';raw.write_bytes(encoded({'role':'user','content':'These outputs are not equivalent quality.'}))
        self.quality['source']['sha256']=sha(raw);self.quality['raw_verdict_quote']='These outputs are not equivalent quality.'
        self.assertFalse(benchmark.summarize(self.suite,self.root,self.quality)['human_quality_confirmed'])

    def test_unknown_attempt_is_not_hidden(self):
        a=dict(self.ledger['attempts'][0]);a['case']='unmatched';self.ledger['attempts'].append(a);self.save()
        with self.assertRaises(FactoryError):benchmark.summarize(self.suite,self.root,self.quality)

    def test_fixture_and_cross_round_source_mismatch_block(self):
        for field in ('fixture_digest','source_digest','settings_digest'):
            before=self.ledger['attempts'][1][field];self.ledger['attempts'][1][field]='wrong';self.save()
            with self.assertRaises(FactoryError):benchmark.summarize(self.suite,self.root,self.quality)
            self.ledger['attempts'][1][field]=before

    def test_rework_all_counted_and_can_remove_savings(self):
        a=dict(self.ledger['attempts'][2]);a.update(kind='rework',role='author_rework',jsonl='repair.jsonl',verdict='FAIL')
        p=self.root/a['jsonl'];p.write_text(json.dumps({'type':'turn.completed','usage':{'input_tokens':9999999,'cached_input_tokens':0,'output_tokens':9}})+'\n')
        a['sha256']=sha(p);self.ledger['attempts'].append(a);self.save()
        result=benchmark.summarize(self.suite,self.root,self.quality)
        self.assertFalse(result['accepted']);self.assertGreater(result['all_attempt_tokens'],9999999)
        self.assertEqual(result['status'],'TOKEN_TARGET_NOT_MET')

    def test_unaccounted_logs_and_changed_final_outputs_block(self):
        (self.root/'orphan.jsonl').write_text('{}\n')
        with self.assertRaises(FactoryError):benchmark.summarize(self.suite,self.root,self.quality)
        (self.root/'orphan.jsonl').unlink();(self.root/'new1/OUT.md').write_text('shortened')
        with self.assertRaises(FactoryError):benchmark.summarize(self.suite,self.root,self.quality)

    def test_failed_review_is_not_process_success(self):
        self.ledger['attempts'][2]['verdict']='FAIL';self.save()
        self.assertEqual(benchmark.summarize(self.suite,self.root,self.quality)['status'],'BENCHMARK_INCOMPLETE')

    def test_author_cannot_rewrite_fixture_authority(self):
        (self.root/'new1/SOURCE.md').write_text('author invented authority')
        self.ledger['runs']['one:new:1']['final_files']=benchmark.tree_files(self.root/'new1');self.save()
        with self.assertRaises(FactoryError):benchmark.summarize(self.suite,self.root,self.quality)

    def test_reviewed_design_changed_after_production_is_rejected(self):
        self.suite['cases'][0]['design_outputs']=['OUT.md']
        self.ledger['suite_sha256']=digest(self.suite)
        for run in self.ledger['runs'].values():run['sealed_design']={'OUT.md':sha(self.root/run['work']/'OUT.md')}
        (self.root/'new1/OUT.md').write_text('B instead of reviewed A')
        self.ledger['runs']['one:new:1']['final_files']=benchmark.tree_files(self.root/'new1');self.save()
        with self.assertRaises(FactoryError):benchmark.summarize(self.suite,self.root,self.quality)

    def test_apply_patch_file_change_is_a_tool_operation(self):
        p=self.root/'patch.jsonl'
        events=[{'type':'item.completed','item':{'id':'patch-1','type':'file_change','status':'completed','changes':[]}},
                {'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':0,'output_tokens':5}}]
        p.write_text('\n'.join(json.dumps(e) for e in events)+'\n')
        self.assertEqual(benchmark.usage(p)['tool_calls'],1)

    def test_missing_usage_stays_incomplete(self):
        p=self.root/'old1.jsonl';p.write_text('{"type":"turn.failed"}\n');self.ledger['attempts'][0]['sha256']=sha(p);self.save()
        self.assertFalse(benchmark.summarize(self.suite,self.root,self.quality)['usage_complete'])

    def test_unmetered_new_attempt_is_not_a_proven_reduction(self):
        p=self.root/'new1.jsonl';p.write_text('{"type":"turn.failed"}\n');self.ledger['attempts'][2]['sha256']=sha(p);self.save()
        comparison=benchmark.summarize(self.suite,self.root,self.quality)['comparisons'][0]
        self.assertTrue(comparison['known_lower'])
        self.assertFalse(comparison['lower'])
        self.assertFalse(comparison['new']['metering_complete'])

class BenchmarkResumeTests(unittest.TestCase):
    def test_exhausted_trial_does_not_skip_other_fixed_trials_or_gain_retries(self):
        from unittest.mock import patch
        import subprocess
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);factory=root/'factory';factory.mkdir();output=root/'run'
            stages=[dict(role='author',kind='author',task='author output'),dict(role='audit',kind='review',task='review output')]
            manifest=dict(model='gpt-6-astra',reasoning='high',permissions='workspace-write',rounds=2,
                session_timeout_seconds=30,max_rework_rounds=1,baseline_revision='0'*40,
                cases=[dict(id='synthetic',task='A bounded synthetic result.',requirements=[],fixtures={'AGENTS.md':'Immutable test rules.'},
                    outputs=['OUT.md'],sources={'old':[],'new':[]},old_stages=stages,new_stages=stages)])
            original=subprocess.run;calls=[]
            def fake(command,**kwargs):
                if command[0]!='codex':return original(command,**kwargs)
                calls.append(command);work=Path(kwargs['cwd']);(work/'OUT.md').write_text('Full synthetic output.')
                verdict='FAIL' if work.name=='synthetic-1-old' and 'CURRENT STAGE\nreview output' in command[-1] else 'PASS'
                events=[dict(type='thread.started',thread_id=f'session-{len(calls)}'),
                        dict(type='item.completed',item=dict(type='agent_message',text=json.dumps(dict(verdict=verdict,findings=[])))),
                        dict(type='turn.completed',usage=dict(input_tokens=10,cached_input_tokens=0,output_tokens=2))]
                kwargs['stdout'].write(('\n'.join(json.dumps(e) for e in events)+'\n').encode())
                return SimpleNamespace(returncode=0)
            with patch.object(benchmark.subprocess,'run',side_effect=fake):
                result=benchmark.run(manifest,factory,output)
                count=len(calls)
                benchmark.run(manifest,factory,output,resume=True)
                self.assertEqual(len(calls),count)
            ledger=json.loads((output/'ATTEMPTS.json').read_text())
            self.assertTrue(ledger['finished'])
            self.assertEqual(len(ledger['runs']),4)
            self.assertEqual(ledger['runs']['synthetic:old:1']['repair_rounds'],1)
            self.assertEqual(result['stopped_runs'],{'synthetic:old:1':'REWORK_LIMIT'})
            self.assertEqual(result['status'],'BENCHMARK_INCOMPLETE')
            self.assertEqual(result['all_attempt_tokens'],len(calls)*12)

    def test_continuing_author_keeps_fixed_permissions_and_work_root(self):
        from unittest.mock import patch
        import subprocess
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);factory=root/'factory';factory.mkdir();output=root/'run'
            stages=[dict(role='author',kind='author',task='first output'),
                    dict(role='author_production',kind='author',task='second output')]
            manifest=dict(model='gpt-6-astra',reasoning='high',permissions='workspace-write',rounds=2,
                session_timeout_seconds=30,max_rework_rounds=2,baseline_revision='0'*40,
                cases=[dict(id='synthetic',task='A bounded synthetic result.',requirements=[],fixtures={'AGENTS.md':'Immutable test rules.'},
                    outputs=['OUT.md'],sources={'old':[],'new':[]},old_stages=stages,new_stages=stages)])
            original=subprocess.run;commands=[]
            def fake(command,**kwargs):
                if command[0]!='codex':return original(command,**kwargs)
                commands.append(command);work=Path(kwargs['cwd'])
                prefix=command[:command.index('resume')] if 'resume' in command else command[:-1]
                self.assertEqual(prefix[prefix.index('--sandbox')+1],'workspace-write')
                self.assertEqual(Path(prefix[prefix.index('-C')+1]),work)
                (work/'OUT.md').write_text('Full synthetic output.')
                events=[dict(type='thread.started',thread_id=f'session-{len(commands)}'),
                        dict(type='item.completed',item=dict(type='agent_message',text=json.dumps(dict(verdict='PASS',findings=[])))),
                        dict(type='turn.completed',usage=dict(input_tokens=10,cached_input_tokens=0,output_tokens=2))]
                kwargs['stdout'].write(('\n'.join(json.dumps(e) for e in events)+'\n').encode())
                return SimpleNamespace(returncode=0)
            with patch.object(benchmark.subprocess,'run',side_effect=fake):
                benchmark.run(manifest,factory,output)
            self.assertEqual(sum('resume' in c for c in commands),2)

    def test_resume_retains_unmetered_failure_without_redoing_completed_author(self):
        from unittest.mock import patch
        import subprocess
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);factory=root/'factory';factory.mkdir();output=root/'run'
            stages=[dict(role='author',kind='author',task='author output'),dict(role='audit',kind='review',task='review output')]
            manifest=dict(model='gpt-6-astra',reasoning='high',permissions='workspace-write',rounds=2,
                session_timeout_seconds=30,max_rework_rounds=2,baseline_revision='0'*40,
                cases=[dict(id='synthetic',task='A bounded synthetic result.',requirements=[],fixtures={'AGENTS.md':'Immutable test rules.'},
                    outputs=['OUT.md'],sources={'old':[],'new':[]},old_stages=stages,new_stages=stages)])
            original=subprocess.run;calls=[];failed=False
            def fake(command,**kwargs):
                nonlocal failed
                if command[0]!='codex':return original(command,**kwargs)
                prompt=command[-1];work=Path(kwargs['cwd']);calls.append(prompt)
                events=[dict(type='thread.started',thread_id=f'session-{len(calls)}'),dict(type='turn.started')]
                code=0
                if 'CURRENT STAGE\nreview output' in prompt and not failed:
                    failed=True;code=1;events.extend([dict(type='error',message='Workspace out of credits.'),dict(type='turn.failed')])
                else:
                    if 'CURRENT STAGE\nauthor output' in prompt:(work/'OUT.md').write_text('Full test output.')
                    events.extend([dict(type='item.completed',item=dict(type='agent_message',text=json.dumps(dict(verdict='PASS',findings=[])))),
                        dict(type='turn.completed',usage=dict(input_tokens=10,cached_input_tokens=0,output_tokens=2))])
                kwargs['stdout'].write(('\n'.join(json.dumps(e) for e in events)+'\n').encode())
                return SimpleNamespace(returncode=code)
            with patch.object(benchmark.subprocess,'run',side_effect=fake):
                first=benchmark.run(manifest,factory,output)
                self.assertFalse(first['usage_complete'])
                second=benchmark.run(manifest,factory,output,resume=True)
            ledger=json.loads((output/'ATTEMPTS.json').read_text())
            self.assertTrue(ledger['finished'])
            self.assertEqual(sum('CURRENT STAGE\nauthor output' in p for p in calls),4)
            self.assertEqual(len(ledger['attempts']),9)
            self.assertEqual(second['all_attempt_tokens'],96)
            self.assertFalse(second['usage_complete']) # Never invent usage for the rejected request.

if __name__=='__main__':unittest.main()
