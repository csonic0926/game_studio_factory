"""Differential stable-filesystem and cache-refusal tests; no game/engine use."""
from pathlib import Path
import hashlib
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from factory_core import state as candidate
from factory_core.refs import FactoryError, confined, encoded, read_json, sha
from factory_core.state import identifier


def original(game, task_id):
    """Independent legacy algorithm oracle, not a cache or production fallback."""
    identifier(task_id)
    game = game.resolve()
    directory = confined(game, f"design/factory/checkpoints/{task_id}")
    paths = sorted(directory.glob("*.json")) if directory.exists() else []
    previous = None
    previous_digest = None
    for generation, path in enumerate(paths, 1):
        confined(game, path.relative_to(game).as_posix())
        record = read_json(path)
        if (path.name != f"{generation:06d}.json" or record.get("generation") != generation
                or record.get("task_id") != task_id or record.get("previous") != previous_digest
                or record.get("schema_version") != "factory_checkpoint.v2"):
            candidate.fail("BROKEN_CHECKPOINT_CHAIN", str(path))
        previous, previous_digest = record, sha(path)
    return previous, previous_digest

class LinkCacheTests(unittest.TestCase):
    def clear_cache(self):
        with candidate._CHECKPOINT_LINK_LOCK:
            candidate._CHECKPOINT_LINKS.clear()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.game=Path(self.tmp.name);self.directory=self.game/"design/factory/checkpoints/task"
        self.directory.mkdir(parents=True);self.clear_cache();self.make_chain()
    def make_chain(self, count=3):
        previous=None
        for generation in range(1,count+1):
            value=dict(schema_version="factory_checkpoint.v2",generation=generation,task_id="task",previous=previous,summary="original",nested={"mutable":[generation]})
            p=self.directory/f"{generation:06d}.json";p.write_bytes(encoded(value));previous=hashlib.sha256(p.read_bytes()).hexdigest()
    def outcome(self, function, game=None):
        try:return ("ok",function(game or self.game,"task"))
        except FactoryError as exc:return ("error",exc.code)
    def equal(self):self.assertEqual(self.outcome(original),self.outcome(candidate.latest))
    def edit(self, sequence, **updates):
        p=self.directory/f"{sequence:06d}.json";value=json.loads(p.read_text());value.update(updates);p.write_bytes(encoded(value))
    def test_valid_cold_and_warm(self):self.equal();self.equal()
    def test_every_file_read_hashed_but_warm_history_not_reparsed(self):
        with patch.object(candidate,"_checkpoint_snapshot",wraps=candidate._checkpoint_snapshot) as read,patch.object(candidate,"_checkpoint_record",wraps=candidate._checkpoint_record) as decode:
            candidate.latest(self.game,"task");self.assertEqual((read.call_count,decode.call_count),(3,3))
            candidate.latest(self.game,"task");self.assertEqual((read.call_count,decode.call_count),(6,4))
    def test_caller_mutation_cannot_poison_latest(self):
        value,_=candidate.latest(self.game,"task");value["generation"]=99;value["nested"]["mutable"].append(99);self.equal()
    def test_oldest_mutation_same_size_same_mtime(self):
        candidate.latest(self.game,"task");p=self.directory/"000001.json";before=p.stat();raw=p.read_bytes();p.write_bytes(raw.replace(b"original",b"modified"));os.utime(p,ns=(before.st_atime_ns,before.st_mtime_ns));self.assertEqual(p.stat().st_size,before.st_size);self.equal();self.assertEqual(self.outcome(candidate.latest),("error","BROKEN_CHECKPOINT_CHAIN"))
    def test_invalid_link_fields_after_warming(self):
        for field,value in [("generation",99),("task_id","other"),("previous","wrong"),("schema_version","wrong")]:
            with self.subTest(field=field):
                self.make_chain();self.clear_cache();candidate.latest(self.game,"task");self.edit(2,**{field:value});self.equal();self.assertEqual(self.outcome(candidate.latest),("error","BROKEN_CHECKPOINT_CHAIN"))
    def test_latest_invalidated_after_warming(self):candidate.latest(self.game,"task");self.edit(3,task_id="other");self.equal()
    def test_latest_stage_and_ruling_payload_never_cached(self):
        candidate.latest(self.game,"task")
        self.edit(3,stage="DRAFT",ruling={"verdict":"USER_REJECTED"})
        self.equal()
        record,_=candidate.latest(self.game,"task")
        self.assertEqual((record["stage"],record["ruling"]["verdict"]),("DRAFT","USER_REJECTED"))
    def test_relinked_history_reads_every_current_hash(self):
        candidate.latest(self.game,"task")
        self.edit(1,summary="changed history")
        for sequence in [2,3]:
            previous=self.directory/f"{sequence-1:06d}.json"
            self.edit(sequence,previous=hashlib.sha256(previous.read_bytes()).hexdigest())
        self.equal()
    def test_invalid_json_after_warming(self):candidate.latest(self.game,"task");(self.directory/"000001.json").write_bytes(b"{");self.equal()
    def test_json_nonobject_after_warming(self):candidate.latest(self.game,"task");(self.directory/"000001.json").write_bytes(b"[]");self.equal()
    def test_utf8_only_and_bom_behavior(self):
        for raw in [b"\xff",b"\xef\xbb\xbf{}",'{}'.encode('utf-16')]:
            with self.subTest(raw=raw):
                (self.directory/"000001.json").write_bytes(raw);self.equal();self.assertEqual(self.outcome(candidate.latest),("error","INVALID_JSON"))
    def test_newline_equivalence(self):
        for newline in [b"\r\n",b"\r"]:
            with self.subTest(newline=newline):
                self.make_chain(1)
                for p in self.directory.glob('*.json'):
                    if p.name!='000001.json':p.unlink()
                p=self.directory/'000001.json';p.write_bytes(p.read_bytes().replace(b'\n',newline));self.equal()
    def test_appended_latest_not_hidden(self):candidate.latest(self.game,"task");self.make_chain(4);self.equal();self.assertEqual(candidate.latest(self.game,"task")[0]["generation"],4)
    def test_removed_tail_not_cached_as_latest(self):candidate.latest(self.game,"task");(self.directory/"000003.json").unlink();self.equal();self.assertEqual(candidate.latest(self.game,"task")[0]["generation"],2)
    def test_removed_middle_rejected(self):candidate.latest(self.game,"task");(self.directory/"000002.json").unlink();self.equal()
    def test_numbering_gap_rejected(self):candidate.latest(self.game,"task");(self.directory/"000003.json").rename(self.directory/"000004.json");self.equal()
    def test_file_symlink_cannot_reuse_cache(self):
        candidate.latest(self.game,"task");p=self.directory/'000001.json';outside=self.game/'target.json';outside.write_bytes(p.read_bytes());p.unlink();p.symlink_to(outside);self.equal();self.assertEqual(self.outcome(candidate.latest),("error","UNSAFE_PATH"))
    def test_directory_symlink_rejected(self):
        candidate.latest(self.game,"task");moved=self.game/'moved';self.directory.rename(moved);self.directory.symlink_to(moved,target_is_directory=True);self.equal()
    def test_eviction_preserves_results(self):
        with patch.object(candidate,'_CHECKPOINT_LINK_LIMIT',2):self.make_chain(5);self.equal();self.equal();self.assertLessEqual(len(candidate._CHECKPOINT_LINKS),2)
    def test_cross_project_does_not_reuse_latest_object(self):
        candidate.latest(self.game,"task");other=self.game/'other';target=other/'design/factory/checkpoints/task';target.mkdir(parents=True)
        p=target/'000001.json';value=dict(schema_version='factory_checkpoint.v2',generation=1,task_id='task',previous=None,summary='different');p.write_bytes(encoded(value));self.assertEqual(self.outcome(original,other),self.outcome(candidate.latest,other));self.assertEqual(candidate.latest(other,'task')[0]['summary'],'different')
    def test_empty_or_missing_chain_returns_none(self):
        for p in self.directory.glob('*.json'):p.unlink()
        self.equal();self.directory.rmdir();self.equal()
    def test_parallel_readers_do_not_poison_cache(self):
        expected=original(self.game,'task')
        with ThreadPoolExecutor(max_workers=4) as pool:
            for actual in pool.map(lambda _:candidate.latest(self.game,'task'),range(24)):self.assertEqual(actual,expected)
    def test_read_only(self):
        before={str(p.relative_to(self.game)):p.read_bytes() for p in self.game.rglob('*') if p.is_file()};candidate.latest(self.game,'task');candidate.latest(self.game,'task');self.assertEqual(before,{str(p.relative_to(self.game)):p.read_bytes() for p in self.game.rglob('*') if p.is_file()})
    def test_concurrent_snapshot_change_fails_closed(self):
        real=candidate.os.fstat;count=0
        def changed(fd):
            nonlocal count
            value=real(fd);count+=1
            if count==2:
                class Changed:pass
                result=Changed()
                for key in ['st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns']:setattr(result,key,getattr(value,key))
                result.st_mtime_ns+=1;return result
            return value
        with patch.object(candidate.os,'fstat',side_effect=changed):self.assertEqual(self.outcome(candidate.latest),("error","BROKEN_CHECKPOINT_CHAIN"))
    def test_legacy_numeric_generation_semantics_unchanged(self):
        for value in [True,1.0]:
            with self.subTest(value=value):
                for p in self.directory.glob('*.json'):p.unlink()
                self.make_chain(1);self.edit(1,generation=value);self.equal()

if __name__=='__main__':unittest.main()
