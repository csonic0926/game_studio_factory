"""Synthetic evidence validates mechanics only, never a real reader or prose verdict."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from factory_core.refs import FactoryError, digest, reference
from player_text import workflow as w


class PlayerTextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.locale_ref = self.write("locales.json", {"shipped": ["en", "zh-Hant"]})
        self.meaning_ref = self.write("meaning.md", "Synthetic test: the button cancels the current operation.")
        self.write("runtime.txt", "Synthetic presentation fixture, not runtime-play evidence.")
        self.write("copy/en.json", {"message": "Please wait for {name}.", "button": "Cancel", "comment": "not shown"})
        self.write("copy/zh.json", {"message": "請等候 {name}。", "button": "取消", "comment": "not shown"})
        self.inventory = dict(schema_version="player_text_inventory.v1", scope="ALL", locales=["en", "zh-Hant"],
            locale_authority=self.locale_ref, context_sources=[self.meaning_ref],
            coverage_notes=["Synthetic fixture only: both collections enumerate this test's entire visible text."],
            runtime_paths=["runtime.txt"], discovery_globs=["copy/*", "runtime.txt"], sources=[
                dict(id=locale, path=path, format="json", locale=locale, kind="functional",
                     context="A confirmation panel, message followed by button.", exclude={"/comment": "Not loaded into the player UI."})
                for locale, path in [("en", "copy/en.json"), ("zh-Hant", "copy/zh.json")]])
        self.save_inventory()

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        return reference(self.root, path)

    def save_inventory(self):
        return self.write("work/inventory.json", self.inventory)

    def prepare(self):
        self.before = w.prepare(self.root, "work/inventory.json")
        self.write("work/before.json", self.before)

    def seal(self):
        self.data = w.seal(self.root, "work/before.json", ["synthetic-author", "synthetic-editor"])
        self.candidate_ref = self.write("work/candidate.json", self.data)

    def reviews(self):
        packet_hash = digest(w.reading_packet(self.data))
        self.reading = dict(schema_version="player_text_reading.v1", packet_sha256=packet_hash,
            reader_context_id="synthetic-reader", reader_kind="AI", fresh=True, sources_read=[packet_hash],
            results=[dict(id=i["id"], understood="Synthetic test interpretation, not a real reading.",
                          status="PASS", rationale="Synthetic checker fixture only.") for i in self.data["items"]])
        self.reading_ref = self.write("work/reading.json", self.reading)
        self.back = dict(schema_version="player_text_backcheck.v1", candidate=self.candidate_ref,
            reading=self.reading_ref, reviewer_context_id="synthetic-backcheck", fresh=True,
            coverage=dict(status="PASS", rationale="Synthetic scope fixture, no human/creative/runtime verdict.",
                evidence=[self.data["inventory"], self.locale_ref, self.meaning_ref, *self.data["outputs"]]),
            results=[dict(id=i["id"], meaning="PASS", language="PASS", presentation="PASS",
                          rationale="Synthetic semantic check fixture only.") for i in self.data["items"]])
        self.write("work/backcheck.json", self.back)

    def check(self):
        return w.check(self.root, "work/candidate.json", "work/reading.json", "work/backcheck.json")

    def ready(self):
        self.prepare(); self.seal(); self.reviews()

    def test_all_locales_every_item_and_no_quality_claim(self):
        self.ready()
        result = self.check()
        self.assertEqual(result["text_count"], 4)
        self.assertEqual(result["scope"], "ALL")
        self.assertFalse(result["human_comprehension_proven"])
        self.assertFalse(result["gameplay_accepted"])
        self.assertEqual({i["disposition"] for i in self.data["items"]}, {"UNCHANGED"})
        self.write("work/receipt.json", result)
        self.assertEqual(w.verify(self.root, "work/receipt.json"), result)
        self.assertFalse((self.root / ".git").exists())

    def test_rewrite_keeps_original_and_binds_landed_text(self):
        self.prepare()
        self.write("copy/en.json", {"message": "Wait for {name}.", "button": "Cancel", "comment": "not shown"})
        self.seal(); self.reviews()
        self.assertEqual(self.check()["text_count"], 4)
        self.assertEqual(sum(i["disposition"] == "REWRITTEN" for i in self.data["items"]), 1)
        self.assertEqual(self.before["items"][0]["text"], "Please wait for {name}.")

    def test_first_reader_packet_hides_keys_sources_originals_and_constraints(self):
        self.prepare(); self.seal()
        plain = w.reading_packet(self.data)
        for item in plain["items"]:
            self.assertEqual(set(item), {"id", "locale", "kind", "context", "text"})
            self.assertRegex(item["id"], r"^[0-9a-f]{64}$")
        self.assertNotIn("copy/en.json", json.dumps(plain))
        self.assertNotIn("protected_forms", json.dumps(plain))

    def test_no_missing_duplicate_or_unknown_result_even_unchanged(self):
        self.ready()
        for rows in (self.reading["results"][:-1], self.reading["results"] + self.reading["results"][:1],
                     [dict(self.reading["results"][0], id="not-known"), *self.reading["results"][1:]]):
            with self.subTest(rows=rows):
                self.write("work/reading.json", dict(self.reading, results=rows))
                with self.assertRaises(FactoryError): self.check()

    def test_reader_producer_overlap_and_design_context_leak_rejected(self):
        self.ready()
        for change in ({"reader_context_id": "synthetic-author"}, {"fresh": False},
                       {"sources_read": [self.reading["packet_sha256"], "design.md"]}):
            with self.subTest(change=change):
                self.write("work/reading.json", {**self.reading, **change})
                with self.assertRaises(FactoryError): self.check()

    def test_backchecker_must_be_distinct_and_cover_all_items(self):
        self.ready()
        for change in ({"reviewer_context_id": "synthetic-reader"}, {"reviewer_context_id": "synthetic-editor"},
                       {"results": self.back["results"][:-1]}):
            with self.subTest(change=change):
                self.write("work/backcheck.json", {**self.back, **change})
                with self.assertRaises(FactoryError): self.check()

    def test_unresolved_reading_and_each_backcheck_dimension_block(self):
        self.ready()
        broken = copy.deepcopy(self.reading); broken["results"][0]["status"] = "REVISE"
        self.write("work/reading.json", broken)
        with self.assertRaisesRegex(FactoryError, "language difficulty"): self.check()
        self.write("work/reading.json", self.reading)
        for key in ("meaning", "language", "presentation"):
            broken = copy.deepcopy(self.back); broken["results"][0][key] = "REVISE"
            self.write("work/backcheck.json", broken)
            with self.assertRaisesRegex(FactoryError, "remains unresolved"): self.check()

    def test_coverage_needs_authority_and_runtime_sources(self):
        self.ready()
        for ref in (self.locale_ref, self.meaning_ref, self.data["outputs"][0]):
            broken = copy.deepcopy(self.back)
            broken["coverage"]["evidence"].remove(ref)
            self.write("work/backcheck.json", broken)
            with self.assertRaisesRegex(FactoryError, "coverage review"): self.check()

    def test_changed_text_runtime_authority_and_review_invalidate_receipt(self):
        for path, value in [("copy/en.json", {"message":"Changed {name}","button":"Cancel","comment":"not shown"}),
                            ("runtime.txt", "Changed layout"), ("meaning.md", "Changed meaning"),
                            ("locales.json", {"shipped":["en"]}), ("work/reading.json", {})]:
            with self.subTest(path=path):
                self.setUp()
                self.ready(); self.write("work/receipt.json", self.check())
                self.write(path, value)
                with self.assertRaises(FactoryError): w.verify(self.root, "work/receipt.json")

    def test_new_key_needs_new_inventory(self):
        self.prepare()
        self.write("copy/en.json", {"message":"Please wait for {name}.","button":"Cancel","comment":"not shown","new":"New UI text"})
        with self.assertRaisesRegex(FactoryError, "membership changed"): self.seal()

    def test_new_source_file_invalidates_whole_game_receipt(self):
        self.ready(); self.write("work/receipt.json", self.check())
        self.write("copy/new-screen.json", {"new_label":"A previously uninventoried player-facing label."})
        with self.assertRaisesRegex(FactoryError, "discovery membership changed"):
            w.verify(self.root,"work/receipt.json")

    def test_all_requires_bounded_nonempty_discovery(self):
        for patterns in ([], ["../outside/*"], ["missing/*.json"]):
            with self.subTest(patterns=patterns):
                self.inventory["discovery_globs"] = patterns; self.save_inventory()
                with self.assertRaises(FactoryError): self.prepare()

    def test_missing_locale_blank_text_and_empty_inventory_fail(self):
        for mutation in (lambda i: i["sources"].pop(), lambda i: i.update(sources=[]),
                         lambda i: i["sources"][0].update(exclude={"/message":"internal","/button":"internal","/comment":"internal"})):
            with self.subTest(mutation=mutation):
                self.setUp(); mutation(self.inventory); self.save_inventory()
                with self.assertRaises(FactoryError): self.prepare()
        self.setUp(); self.write("copy/en.json", {"message":"", "button":"Cancel", "comment":"not shown"})
        with self.assertRaises(FactoryError): self.prepare()

    def test_placeholder_and_protected_form_counts_preserved(self):
        for value in ("Please wait.", "Please wait for {other}.", "{name} {name}"):
            with self.subTest(value=value):
                self.setUp(); self.prepare()
                self.write("copy/en.json", {"message":value,"button":"Cancel","comment":"not shown"})
                with self.assertRaisesRegex(FactoryError, "placeholder"): self.seal()
        self.setUp(); self.inventory["sources"][0]["overrides"] = {"/button":{"protected_forms":["Cancel"]}}
        self.save_inventory(); self.prepare()
        self.write("copy/en.json", {"message":"Please wait for {name}.","button":"Return","comment":"not shown"})
        with self.assertRaisesRegex(FactoryError, "protected form"): self.seal()

    def test_duplicate_json_keys_fail_instead_of_losing_text(self):
        self.write("copy/en.json", '{"message":"first", "message":"second"}')
        with self.assertRaisesRegex(FactoryError, "duplicate JSON key"): self.prepare()

    def test_csv_multiline_locale_columns_and_row_shape(self):
        self.write("copy/all.csv", 'key,en,zh\nmessage,"Line one\nLine two",兩行\nbutton,Cancel,取消\n')
        self.inventory["sources"] = [dict(id=l, path="copy/all.csv", format="csv", locale=l,
            kind="functional", context="Synthetic panel.", options={"key_column":"key","text_column":c})
            for l,c in [("en","en"),("zh-Hant","zh")]]
        self.save_inventory(); self.prepare(); self.seal(); self.reviews()
        self.assertEqual(self.check()["text_count"], 4)
        self.assertIn("\n", self.data["items"][0]["text"])
        self.write("copy/all.csv", 'key,en,zh\na,One,一\na,Two,二\n')
        with self.assertRaisesRegex(FactoryError, "duplicate CSV"): self.prepare()
        self.write("copy/all.csv", 'key,en,zh\na,One\n')
        with self.assertRaisesRegex(FactoryError, "row width"): self.prepare()

    def test_text_and_media_export_bindings(self):
        self.write("copy/en.txt", "A complete narration paragraph.")
        self.write("images/title.bin", b"image fixture".decode())
        self.inventory["sources"][0].update(path="copy/en.txt", format="text", kind="narration",
            exclude={}, rendered_paths=["images/title.bin"])
        self.save_inventory(); self.ready()
        self.assertEqual(self.check()["text_count"], 3)
        self.write("images/title.bin", "changed image text")
        with self.assertRaises(FactoryError): self.check()

    def test_array_catalog_receipt_expands_through_factory_reference_closure(self):
        self.write("copy/en.json", '\ufeff["Please wait for {name}.", "Cancel"]')
        self.inventory["sources"][0]["exclude"] = {}
        self.save_inventory(); self.ready()
        receipt = self.write("work/receipt.json", self.check())
        from factory_core.refs import expand_references
        refs = expand_references({"game":self.root,"factory":w.FACTORY},[receipt])
        self.assertIn(reference(self.root,"copy/en.json"),refs)

    def test_factory_dependency_sets_keep_workflow_v3_only(self):
        from factory_core.catalog import factory_dependencies
        for capability in sorted(w.PRODUCERS):
            task = "chapter" if capability == "story" else "fixture"
            with self.subTest(capability=capability):
                native = {r["path"] for r in factory_dependencies(w.FACTORY,capability,task,3)}
                legacy = {r["path"] for r in factory_dependencies(w.FACTORY,capability,task,2)}
                self.assertIn("player_text/WORKFLOW.md",native)
                self.assertIn("player_text/workflow.py",native)
                self.assertFalse(any(p.startswith("player_text/") for p in legacy))

    def test_json_subtrees_escaped_selectors_and_mixed_kinds(self):
        self.write("copy/en.json", {"a/b":{"~title":"A room."}, "internal":"not selected"})
        self.inventory["sources"][0].update(options={"pointer":"/a~1b"}, exclude={},
            overrides={"/a~1b/~0title":{"kind":"description","context":"A room label."}})
        self.save_inventory(); self.prepare()
        self.assertEqual(self.before["items"][0]["kind"], "description")
        self.assertEqual(self.before["items"][0]["key"], "/a~1b/~0title")

    def test_unknown_exclusion_and_overlapping_source_rejected(self):
        self.inventory["sources"][0]["exclude"]["/missing"]="not present"
        self.save_inventory()
        with self.assertRaises(FactoryError): self.prepare()
        self.setUp(); self.inventory["sources"].append({**self.inventory["sources"][0],"id":"other"})
        self.save_inventory()
        with self.assertRaisesRegex(FactoryError, "overlapping"): self.prepare()

    def test_stale_extra_presentation_evidence_blocks_verify(self):
        self.ready(); extra=self.write("render.log", "Synthetic render check.")
        self.back["coverage"]["evidence"].append(extra); self.write("work/backcheck.json",self.back)
        self.write("work/receipt.json",self.check()); self.write("render.log","changed")
        with self.assertRaises(FactoryError): w.verify(self.root,"work/receipt.json")

    def test_paths_cannot_escape_or_follow_symlink(self):
        for path in ("../outside.json", "/absolute.json", "copy/../en.json", ".git/config"):
            self.inventory["sources"][0]["path"] = path; self.save_inventory()
            with self.assertRaises(FactoryError): self.prepare()
        self.setUp(); (self.root/"copy/link.json").symlink_to(self.root/"copy/en.json")
        self.inventory["sources"][0]["path"]="copy/link.json"; self.save_inventory()
        with self.assertRaises(FactoryError): self.prepare()
        with self.assertRaises(FactoryError): w.project_root(w.FACTORY)
        with self.assertRaises(FactoryError): w.project_root(w.FACTORY.parent)

    def test_cli_is_external_and_does_not_overwrite(self):
        command=["python3",str(w.FACTORY/"player_text/player_text.py"),"prepare","--project-root",str(self.root),
                 "--inventory","work/inventory.json","--out","work/before.json"]
        first=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
        self.assertEqual(first.returncode,0,first.stdout+first.stderr)
        original=(self.root/"work/before.json").read_bytes()
        second=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
        self.assertEqual(second.returncode,2)
        self.assertEqual(original,(self.root/"work/before.json").read_bytes())

    def test_factory_binding_requires_reviewed_scope_and_exact_receipt(self):
        artifact=self.write("design.md","Synthetic scope: all test player copy.")
        design=dict(schema_version="factory_design.v3",capability="asset",author_context_id="synthetic-author",
                    artifacts=[artifact],production_scope=["work/receipt.json","copy/en.json"])
        roots={"game":self.root,"factory":w.FACTORY}
        with self.assertRaisesRegex(FactoryError,"declare ALL"): w.validate_design(roots,design)
        design["player_text"]=dict(scope="ALL",scope_evidence=artifact,receipt_path="work/receipt.json")
        w.validate_design(roots,design)
        self.ready();receipt=self.write("work/receipt.json",self.check())
        record=dict(stage="EVIDENCE_READY",artifacts=[receipt,reference(self.root,"copy/en.json")])
        w.validate_checkpoint(roots,record,design)
        record["artifacts"].pop()
        with self.assertRaisesRegex(FactoryError,"latest produced files"): w.validate_checkpoint(roots,record,design)
        record["artifacts"]=[]
        with self.assertRaisesRegex(FactoryError,"exact text receipt"): w.validate_checkpoint(roots,record,design)

    def test_none_is_not_empty_pass_and_v2_semantics_are_unchanged(self):
        artifact=self.write("design.md","Synthetic non-text asset scope.")
        design=dict(schema_version="factory_design.v3",capability="asset",artifacts=[artifact],production_scope=["art.png"],
                    player_text=dict(scope="NONE",scope_evidence=artifact,receipt_path=None))
        roots={"game":self.root,"factory":w.FACTORY}; w.validate_design(roots,design)
        w.validate_checkpoint(roots,dict(stage="EVIDENCE_READY",artifacts=[]),design)
        design["schema_version"]="factory_design.v2"
        with self.assertRaisesRegex(FactoryError,"explicit v3"): w.validate_design(roots,design)
        del design["player_text"]; w.validate_design(roots,design)
        from factory_core.state import requirement_ids
        self.assertNotIn("player_text.complete_coverage_and_meaning",requirement_ids(w.FACTORY,{**design,"requirements":{}},"intent_experience"))


class PlayerTextCheckpointTests(unittest.TestCase):
    """Exercise the real v3 state boundary, not only the standalone helper."""
    from factory_core.tests.test_gpt6 import Gpt6Tests as _fixtures
    setUp = _fixtures.setUp
    write = _fixtures.write
    migrate = _fixtures.migrate
    design = _fixtures.design
    request = _fixtures.request

    def test_real_v3_evidence_boundary_requires_receipt_and_rechecks_latest_output(self):
        from factory_core.state import checkpoint, latest, approval_action, verify_record
        from factory_core.tests.test_core import CoreTests
        d, _ = self.design()
        d["production_scope"] += ["copy/en.json", "work/receipt.json"]
        d["player_text"] = dict(scope="CHANGED", scope_evidence=d["artifacts"][0], receipt_path="work/receipt.json")
        design_ref = self.write("design/assets/PACKAGE.json", d)
        out = checkpoint(self.roots,self.request("DESIGN_COMPLETE",design=design_ref))
        record,_ = latest(self.game,"lantern")
        reviews = CoreTests.reviews(self,d,design_ref,record["dependencies"])
        out = checkpoint(self.roots,self.request("REVIEWED",out["checkpoint"]["sha256"],design=design_ref,reviews=reviews))
        quote=approval_action(design_ref,record["dependencies"])
        raw=self.write("synthetic-user.json",dict(role="user",content=quote))
        ruling=self.write("synthetic-ruling.json",dict(schema_version="factory_ruling.v2",owner="USER",decision="APPROVE",
            design=design_ref,dependency_fingerprint=record["dependencies"]["fingerprint"],source=raw,quote=quote))
        for stage in ("AUTHORIZED","PRODUCING"):
            out=checkpoint(self.roots,self.request(stage,out["checkpoint"]["sha256"],design=design_ref,reviews=reviews,ruling=ruling))
        output=self.write("copy/en.json",{"title":"A warm lantern."})
        request=self.request("EVIDENCE_READY",out["checkpoint"]["sha256"],design=design_ref,reviews=reviews,ruling=ruling)
        request["artifacts"]=[output]
        with self.assertRaises(FactoryError): checkpoint(self.roots,request)
        self.assertEqual(latest(self.game,"lantern")[0]["stage"],"PRODUCING")

        self.root=self.game
        self.locale_ref=self.write("locale-scope.json",{"shipped":["en"]})
        self.meaning_ref=d["artifacts"][0]
        self.inventory=dict(schema_version="player_text_inventory.v1",scope="CHANGED",locales=["en"],
            locale_authority=self.locale_ref,context_sources=[self.meaning_ref],coverage_notes=["Synthetic one-label fixture."],
            runtime_paths=[],sources=[dict(id="label",path="copy/en.json",format="json",locale="en",
                                          kind="description",context="Synthetic asset label.")])
        self.write("work/inventory.json",self.inventory)
        self.write("work/before.json",w.prepare(self.game,"work/inventory.json"))
        self.data=w.seal(self.game,"work/before.json",["author"])
        self.candidate_ref=self.write("work/candidate.json",self.data)
        PlayerTextTests.reviews(self)
        receipt=self.write("work/receipt.json",w.check(self.game,"work/candidate.json","work/reading.json","work/backcheck.json"))
        request["artifacts"]=[output,receipt]
        checkpoint(self.roots,request)
        record,_=latest(self.game,"lantern")
        verify_record(self.roots,record)
        self.write("copy/en.json",{"title":"Changed after review."})
        with self.assertRaises(FactoryError): verify_record(self.roots,record)


if __name__ == "__main__": unittest.main()
