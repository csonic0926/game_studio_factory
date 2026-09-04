import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SETUP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "setup.py")
spec = importlib.util.spec_from_file_location("factory_setup", SETUP_PATH)
factory_setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(factory_setup)


def make_factory(root, skills=("game-story-factory",)):
    for name in skills:
        skill_dir = os.path.join(root, "story", "skills", name)
        os.makedirs(skill_dir, exist_ok=True)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
            handle.write("# %s\n" % name)
    return root


def make_root_skill(root, name):
    skill_dir = os.path.join(root, "skills", name)
    os.makedirs(skill_dir, exist_ok=True)
    with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
        handle.write("# %s\n" % name)
    return skill_dir


class DiscoverSkillsTest(unittest.TestCase):
    def test_finds_nested_skill_dirs(self):
        with tempfile.TemporaryDirectory() as root:
            make_factory(root, ("alpha", "beta"))
            names = [name for name, _ in factory_setup.discover_skills(root)]
            self.assertEqual(names, ["alpha", "beta"])

    def test_finds_umbrella_and_department_skills(self):
        with tempfile.TemporaryDirectory() as root:
            make_factory(root, ("game-story-factory",))
            make_root_skill(root, "init-game-ai-factory")
            names = [name for name, _ in factory_setup.discover_skills(root)]
            self.assertEqual(names, ["game-story-factory", "init-game-ai-factory"])

    def test_finds_studio_operator_and_canonical_initializer(self):
        with tempfile.TemporaryDirectory() as root:
            studio_skill = os.path.join(root, "studio", "skills", "game-studio-factory")
            os.makedirs(studio_skill)
            with open(os.path.join(studio_skill, "SKILL.md"), "w", encoding="utf-8") as handle:
                handle.write("# game-studio-factory\n")
            make_root_skill(root, "init-game-studio-factory")
            names = [name for name, _ in factory_setup.discover_skills(root)]
            self.assertEqual(
                names, ["game-studio-factory", "init-game-studio-factory"]
            )

    def test_rejects_duplicate_skill_names_across_roots(self):
        with tempfile.TemporaryDirectory() as root:
            make_factory(root, ("duplicate",))
            make_root_skill(root, "duplicate")
            with self.assertRaises(SystemExit):
                factory_setup.discover_skills(root)

    def test_ignores_dirs_without_skill_md(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "story", "skills", "empty"))
            self.assertEqual(factory_setup.discover_skills(root), [])


class SyncSkillsTest(unittest.TestCase):
    def test_loads_legacy_manifest_when_canonical_manifest_is_absent(self):
        with tempfile.TemporaryDirectory() as target:
            legacy = {
                "factory_root": "/legacy/checkout",
                "skills": {"idea-factory": {"mode": "link", "version": "old"}},
            }
            with open(
                os.path.join(target, factory_setup.LEGACY_MANIFEST_NAME),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(legacy, handle)
            self.assertEqual(legacy, factory_setup.load_manifest(target))

    def test_creates_symlink_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            target = os.path.join(root, "skills")
            os.makedirs(target)
            factory_setup.sync_skills(factory, [target])
            dest = os.path.join(target, "game-story-factory")
            self.assertTrue(os.path.islink(dest))
            report = factory_setup.sync_skills(factory, [target])
            self.assertTrue(any(line.startswith("ok ") for line in report))

    def test_never_touches_foreign_entries(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            target = os.path.join(root, "skills")
            foreign = os.path.join(target, "game-story-factory")
            os.makedirs(foreign)
            marker = os.path.join(foreign, "user_owned.txt")
            with open(marker, "w", encoding="utf-8") as handle:
                handle.write("mine\n")
            report = factory_setup.sync_skills(factory, [target])
            self.assertTrue(any("CONFLICT" in line for line in report))
            self.assertTrue(os.path.isfile(marker))

    def test_removes_stale_factory_links(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"), ("alpha", "beta"))
            target = os.path.join(root, "skills")
            os.makedirs(target)
            factory_setup.sync_skills(factory, [target])
            import shutil
            shutil.rmtree(os.path.join(factory, "story", "skills", "beta"))
            factory_setup.sync_skills(factory, [target])
            self.assertFalse(os.path.lexists(os.path.join(target, "beta")))
            self.assertTrue(os.path.islink(os.path.join(target, "alpha")))

    def test_dedupes_targets_resolving_to_same_dir(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            target = os.path.join(root, "skills")
            os.makedirs(target)
            alias = os.path.join(root, "skills_alias")
            os.symlink(target, alias)
            report = factory_setup.sync_skills(factory, [target, alias])
            self.assertTrue(any("same directory" in line for line in report))

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            target = os.path.join(root, "skills")
            os.makedirs(target)
            factory_setup.sync_skills(factory, [target], dry_run=True)
            self.assertEqual(os.listdir(target), [])

    def test_install_creates_missing_target_and_locator_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            make_root_skill(factory, "init-game-ai-factory")
            target = os.path.join(root, "new", "skills")
            factory_setup.sync_skills(factory, [target])
            self.assertTrue(os.path.islink(os.path.join(target, "game-story-factory")))
            self.assertTrue(os.path.islink(os.path.join(target, "init-game-ai-factory")))
            with open(
                os.path.join(target, factory_setup.MANIFEST_NAME), encoding="utf-8"
            ) as handle:
                manifest = json.load(handle)
            self.assertEqual(manifest["factory_root"], factory)
            self.assertEqual(manifest["skills"]["init-game-ai-factory"]["mode"], "link")

    def test_install_command_and_sync_alias_are_both_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            install_target = os.path.join(root, "install")
            sync_target = os.path.join(root, "sync")
            self.assertEqual(
                factory_setup.main(["install", "--target", install_target]), 0
            )
            self.assertEqual(
                factory_setup.main(["sync", "--target", sync_target]), 0
            )
            self.assertTrue(os.path.islink(os.path.join(install_target, "gameplay-factory")))
            self.assertTrue(os.path.islink(os.path.join(sync_target, "gameplay-factory")))


class MarkedBlockTest(unittest.TestCase):
    def test_insert_then_replace_without_duplication(self):
        block = factory_setup.render_routing_block()
        text = factory_setup.upsert_marked_block("# Existing rules\n", block)
        self.assertEqual(text.count(factory_setup.BLOCK_BEGIN), 1)
        self.assertIn("# Existing rules", text)
        again = factory_setup.upsert_marked_block(text, block)
        self.assertEqual(again.count(factory_setup.BLOCK_BEGIN), 1)
        self.assertEqual(again.count(factory_setup.BLOCK_END), 1)

    def test_replacement_preserves_text_after_block(self):
        block = factory_setup.render_routing_block()
        text = factory_setup.upsert_marked_block("intro\n", block) + "\n## Tail section\n"
        replaced = factory_setup.upsert_marked_block(text, block)
        self.assertIn("## Tail section", replaced)


class LinkGameRepoTest(unittest.TestCase):
    def test_link_writes_all_surfaces_idempotently(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            game = os.path.join(root, "game")
            os.makedirs(game)
            with open(os.path.join(game, "AGENTS.md"), "w", encoding="utf-8") as handle:
                handle.write("# Game rules\n")
            factory_setup.link_game_repo(factory, game)
            pointer = os.path.join(game, "design", "STUDIO_FACTORY.local.md")
            self.assertTrue(os.path.isfile(pointer))
            with open(pointer, encoding="utf-8") as handle:
                body = handle.read()
                self.assertIn(factory, body)
                self.assertIn("STUDIO_ROOT:", body)
                self.assertIn("FACTORY_ROOT:", body)
            with open(os.path.join(game, ".gitignore"), encoding="utf-8") as handle:
                self.assertIn("design/STUDIO_FACTORY.local.md", handle.read())
            self.assertTrue(os.path.isfile(os.path.join(game, "CLAUDE.md")))
            factory_setup.link_game_repo(factory, game)
            with open(os.path.join(game, "AGENTS.md"), encoding="utf-8") as handle:
                body = handle.read()
            self.assertEqual(body.count(factory_setup.BLOCK_BEGIN), 1)
            self.assertIn("# Game rules", body)
            self.assertIn("`idea-factory` skill", body)
            self.assertIn("`gameplay-factory` skill", body)
            self.assertIn("`game-studio-factory` skill", body)
            self.assertIn("fresh player-facing interaction", body)
            self.assertIn("PROJECT_GAMEPLAY_PROFILE.md", body)
            self.assertIn("fresh project-standard review", body)
            self.assertIn("blind observation", body)

    def test_existing_claude_md_is_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            game = os.path.join(root, "game")
            os.makedirs(game)
            with open(os.path.join(game, "CLAUDE.md"), "w", encoding="utf-8") as handle:
                handle.write("user content\n")
            factory_setup.link_game_repo(factory, game)
            with open(os.path.join(game, "CLAUDE.md"), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "user content\n")

    def test_refuses_factory_as_game_repo(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            with self.assertRaises(SystemExit):
                factory_setup.link_game_repo(factory, os.path.join(factory, "story"))

    def test_accepts_sibling_whose_name_starts_with_factory_path(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            game = os.path.join(root, "factory-game")
            os.makedirs(game)
            factory_setup.link_game_repo(factory, game)
            self.assertTrue(
                os.path.isfile(os.path.join(game, "design", "STUDIO_FACTORY.local.md"))
            )

    def test_relink_replaces_legacy_marked_block_without_duplication(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            game = os.path.join(root, "game")
            os.makedirs(game)
            legacy = (
                factory_setup.BLOCK_BEGIN
                + "\nold Game AI Factory body\n"
                + factory_setup.BLOCK_END
                + "\n"
            )
            with open(os.path.join(game, "AGENTS.md"), "w", encoding="utf-8") as handle:
                handle.write(legacy)
            factory_setup.link_game_repo(factory, game)
            with open(os.path.join(game, "AGENTS.md"), encoding="utf-8") as handle:
                body = handle.read()
            self.assertEqual(1, body.count(factory_setup.BLOCK_BEGIN))
            self.assertIn("Game Studio Factory routing", body)
            self.assertNotIn("old Game AI Factory body", body)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            factory = make_factory(os.path.join(root, "factory"))
            game = os.path.join(root, "game")
            os.makedirs(game)
            factory_setup.link_game_repo(factory, game, dry_run=True)
            self.assertFalse(os.path.exists(os.path.join(game, "design")))
            self.assertFalse(os.path.exists(os.path.join(game, "CLAUDE.md")))


class ShippedSkillContractTest(unittest.TestCase):
    def test_public_entry_skills_have_valid_minimal_frontmatter(self):
        root = os.path.dirname(SETUP_PATH)
        expected = {
            "idea-factory": os.path.join(
                root, "idea", "skills", "idea-factory", "SKILL.md"
            ),
            "init-game-ai-factory": os.path.join(
                root, "skills", "init-game-ai-factory", "SKILL.md"
            ),
            "init-game-studio-factory": os.path.join(
                root, "skills", "init-game-studio-factory", "SKILL.md"
            ),
            "gameplay-factory": os.path.join(
                root, "gameplay", "skills", "gameplay-factory", "SKILL.md"
            ),
            "game-studio-factory": os.path.join(
                root, "studio", "skills", "game-studio-factory", "SKILL.md"
            ),
            "studio-semantic-alignment-reviewer": os.path.join(
                root,
                "studio",
                "skills",
                "studio-semantic-alignment-reviewer",
                "SKILL.md",
            ),
            "studio-gameplay-decision-card-reviewer": os.path.join(
                root,
                "studio",
                "skills",
                "studio-gameplay-decision-card-reviewer",
                "SKILL.md",
            ),
            "studio-player-facing-interaction-reviewer": os.path.join(
                root, "studio", "skills", "studio-player-facing-interaction-reviewer", "SKILL.md"
            ),
            "studio-blind-player-observer": os.path.join(
                root, "studio", "skills", "studio-blind-player-observer", "SKILL.md"
            ),
            "studio-player-facing-evidence-comparison-reviewer": os.path.join(
                root, "studio", "skills", "studio-player-facing-evidence-comparison-reviewer", "SKILL.md"
            ),
        }
        for name, path in expected.items():
            with self.subTest(skill=name), open(path, encoding="utf-8") as handle:
                body = handle.read()
            self.assertTrue(body.startswith("---\n"))
            self.assertIn("\nname: %s\n" % name, body)
            self.assertIn("\ndescription: ", body)
            self.assertNotIn("TODO", body)

    def test_repository_discovery_exposes_all_public_skills(self):
        root = os.path.dirname(SETUP_PATH)
        names = [name for name, _ in factory_setup.discover_skills(root)]
        self.assertEqual(
            names,
            [
                "game-story-factory",
                "game-studio-factory",
                "gameplay-factory",
                "idea-factory",
                "init-game-ai-factory",
                "init-game-studio-factory",
                "studio-blind-player-observer",
                "studio-gameplay-decision-card-reviewer",
                "studio-player-facing-evidence-comparison-reviewer",
                "studio-player-facing-interaction-reviewer",
                "studio-semantic-alignment-reviewer",
            ],
        )

    def test_public_surfaces_do_not_pin_one_developer_checkout(self):
        root = Path(os.path.dirname(SETUP_PATH))
        public_files = [
            root / "README.md",
            root / "STUDIO_CALLER_LANDING.md",
            root / "asset/README.md",
            root / "asset/docs/AI_CALLER_LANDING.md",
            root / "asset/docs/FLOOR_REFERENCE_PAIR_WORKFLOW.md",
            root / "asset/docs/REFERENCE_PAIR_WORKFLOW.md",
            root / "asset/docs/WALL_REFERENCE_PAIR_WORKFLOW.md",
            root / "sound/README.md",
            root / "sound/docs/AI_CALLER_LANDING.md",
            root / "sound/examples/door_open.spec.json",
            root / "story/README.md",
        ]
        public_files.extend(
            Path(path) / "SKILL.md"
            for _, path in factory_setup.discover_skills(root)
        )
        forbidden = "/Users/hunglingki/git_projects/tools/game_ai_factory"
        for path in public_files:
            with self.subTest(path=str(path)):
                self.assertNotIn(forbidden, Path(path).read_text(encoding="utf-8"))

    def test_story_history_is_owned_by_story_not_the_studio_root(self):
        root = Path(os.path.dirname(SETUP_PATH))
        historical_names = [
            "STORY_FACTORY_BUGS_2026-07-07.md",
            "STORY_FACTORY_STAGING_STEP_DESIGN.md",
            "STORY_REBUILD_PLAN.md",
        ]
        for name in historical_names:
            with self.subTest(name=name):
                self.assertFalse((root / name).exists())
                self.assertTrue((root / "story/docs/history" / name).is_file())


if __name__ == "__main__":
    unittest.main()
