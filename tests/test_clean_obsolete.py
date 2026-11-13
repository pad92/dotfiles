import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_fixtures import git, repository

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "clean_obsolete", SCRIPTS / "clean_obsolete.py"
)
clean = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(clean)


class HomeTestCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()

    def config(self):
        managed = clean.managed
        defaults = managed.DataLoader().load_from_file(
            str(managed.DOTFILES_DEFAULTS), trusted_as_template=True
        )
        variables = {**defaults, "dotfiles_home": str(self.home)}
        templar = managed.Templar(loader=managed.DataLoader(), variables=variables)
        return {
            name: templar.template(variables[name]) for name in managed.PATH_VARIABLES
        }

    def link(self, relative: str, target: str) -> Path:
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        return path


class HomeBrokenLinkTests(HomeTestCase):
    def test_lists_broken_links_under_managed_paths_only(self):
        into_clone = self.link(
            ".vim", str(self.home / ".dotfiles/ansible/roles/dotfiles/files/home/.vim")
        )
        unit = self.link(
            ".config/systemd/user/default.target.wants/gone.service",
            "/nonexistent/gone.service",
        )
        script = self.link(".bin/retired.sh", "../.dotfiles/retired.sh")
        (self.home / ".zshrc.real").write_text("")
        self.link(".zshrc", ".zshrc.real")
        self.link(".steampath", "/nonexistent/steam")
        self.link(".config/discord/SingletonLock", "PadsTower-1")

        result = clean.home_broken_links(self.home, self.config())

        self.assertEqual(result, sorted([into_clone, unit, script]))

    def test_does_not_look_through_a_linked_parent(self):
        outside = self.root / "outside"
        (outside / "hypr").mkdir(parents=True)
        (outside / "hypr" / "broken.lua").symlink_to("/nonexistent")
        self.link(".config", str(outside))

        self.assertEqual(clean.home_broken_links(self.home, self.config()), [])


class BackupTests(HomeTestCase):
    def backup(self) -> Path:
        backup = self.home / ".zshrc.bak"
        backup.write_text("previous .zshrc")
        return backup

    def test_plan_lists_managed_backups_only(self):
        backup = self.backup()
        timestamped = self.home / ".zshrc.123.2026-10-16@12:00:00~"
        timestamped.write_text("older .zshrc")
        (self.home / "notes.bak").write_text("not a managed path")

        backups = clean.managed.find_backups(self.home, self.config())

        self.assertEqual(sorted(backups), sorted([backup, timestamped]))

    def test_backups_are_kept_without_a_terminal(self):
        backup = self.backup()
        plan = clean.Plan(backups=[backup])

        clean.confirm_removal(plan, prompt=self.fail, interactive=False)
        clean.apply(plan, self.home)

        self.assertEqual(backup.read_text(), "previous .zshrc")
        self.assertIn("no terminal", plan.kept[0])

    def test_backups_are_kept_unless_remove_is_typed(self):
        backup = self.backup()
        plan = clean.Plan(backups=[backup])

        clean.confirm_removal(plan, prompt=lambda _: "yes", interactive=True)
        clean.apply(plan, self.home)

        self.assertTrue(backup.exists())
        self.assertIn("not confirmed", plan.kept[0])

    def test_typing_remove_deletes_files_links_and_trees(self):
        backup = self.backup()
        tree = self.home / ".vim.bak"
        (tree / "colors").mkdir(parents=True)
        (tree / "colors" / "x.vim").write_text("")
        target = self.root / "target"
        target.write_text("kept")
        link = self.home / ".tmux.bak"
        link.symlink_to(target)
        plan = clean.Plan(backups=[backup, tree, link])

        clean.confirm_removal(plan, prompt=lambda _: "REMOVE\n", interactive=True)
        clean.apply(plan, self.home)

        self.assertFalse(backup.exists())
        self.assertFalse(tree.exists())
        self.assertFalse(link.is_symlink())
        self.assertEqual(target.read_text(), "kept")


class RepositoryTests(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.repository = self.root / "dotfiles"
        repository(self.repository)
        (self.repository / "README").write_text("dotfiles\n")
        git(self.repository, "add", "README")
        git(self.repository, "commit", "-q", "-m", "init")
        self.upstream = self.root / "upstream"
        repository(self.upstream)
        (self.upstream / "plugin.vim").write_text("\n")
        git(self.upstream, "add", "plugin.vim")
        git(self.upstream, "commit", "-q", "-m", "plugin")

    def retired_submodule(self, name: str, local_commit: bool = False) -> Path:
        """A submodule clone left in .git/modules after its removal."""
        checkout = self.root / "checkouts" / name
        git(self.root, "clone", "-q", str(self.upstream), str(checkout))
        if local_commit:
            git(checkout, "config", "commit.gpgsign", "false")
            git(checkout, "config", "user.name", "Test")
            git(checkout, "config", "user.email", "test@example.invalid")
            git(checkout, "switch", "-q", "-c", "mine")
            (checkout / "local.zsh").write_text("\n")
            git(checkout, "add", "local.zsh")
            git(checkout, "commit", "-q", "-m", "local work")
        git_directory = self.repository / ".git" / "modules" / name
        git_directory.parent.mkdir(parents=True, exist_ok=True)
        (checkout / ".git").rename(git_directory)
        git(git_directory, "config", "core.bare", "false")
        git(git_directory, "config", "core.worktree", f"../../../../{name}")
        config = str(self.repository / ".git" / "config")
        git(
            self.repository,
            "config",
            "--file",
            config,
            f"submodule.{name}.url",
            str(self.upstream),
        )
        git(
            self.repository,
            "config",
            "--file",
            config,
            f"submodule.{name}.active",
            "true",
        )
        return git_directory

    def plan(self):
        plan = clean.Plan()
        clean.submodule_leftovers(self.repository, plan)
        return plan

    def test_removes_retired_submodule_whose_commits_are_upstream(self):
        git_directory = self.retired_submodule(".vim/bundle/Vundle.vim")

        plan = self.plan()
        self.assertEqual(plan.submodule_sections, [".vim/bundle/Vundle.vim"])
        self.assertEqual(plan.submodule_directories, [git_directory.resolve()])

        clean.apply(plan, self.repository)
        self.assertFalse((self.repository / ".git" / "modules").exists())
        self.assertNotIn(
            "submodule", git(self.repository, "config", "--list", "--local")
        )

    def test_keeps_clone_with_a_local_commit(self):
        self.retired_submodule("zsh/plugins/zsh-completions", local_commit=True)

        plan = self.plan()
        self.assertEqual(plan.submodule_sections, [])
        self.assertEqual(plan.submodule_directories, [])
        self.assertIn("no remote branch or tag holds", plan.kept[0])

    def test_retired_submodule_is_kept_without_a_terminal(self):
        git_directory = self.retired_submodule("dotbot")
        plan = self.plan()

        clean.confirm_removal(plan, prompt=self.fail, interactive=False)
        clean.apply(plan, self.repository)

        self.assertTrue(git_directory.is_dir())
        self.assertIn(
            "submodule.dotbot.url",
            git(self.repository, "config", "--list", "--local"),
        )
        self.assertIn("1 retired submodules: no terminal", plan.kept[-1])

    def test_removes_section_left_without_url(self):
        git(self.repository, "config", "submodule.dotbot.active", "true")

        plan = self.plan()

        self.assertEqual(plan.submodule_sections, ["dotbot"])

    def test_keeps_nested_clone_with_a_local_commit(self):
        git_directory = self.retired_submodule("vim")
        nested = self.retired_submodule("nested", local_commit=True)
        git(self.repository, "config", "--remove-section", "submodule.nested")
        (git_directory / "modules").mkdir()
        nested.rename(git_directory / "modules" / "nested")

        plan = self.plan()

        self.assertEqual(plan.submodule_directories, [])
        self.assertIn("no remote branch or tag holds", plan.kept[0])

    def test_main_worktree_path_may_contain_spaces(self):
        spaced = self.root / "dot files"
        repository(spaced)

        self.assertTrue(clean.is_main_worktree(spaced))

    def test_prunes_worktree_records_after_confirmation(self):
        worktree = self.root / "gone"
        git(self.repository, "worktree", "add", "-q", str(worktree))
        shutil.rmtree(worktree)
        plan = clean.Plan(prunable_worktrees=clean.prunable_worktrees(self.repository))
        self.assertEqual(len(plan.prunable_worktrees), 1)

        clean.confirm_removal(plan, prompt=lambda _: "REMOVE", interactive=True)
        clean.apply(plan, self.repository)

        self.assertEqual(clean.prunable_worktrees(self.repository), [])

    def test_dry_run_changes_nothing(self):
        git_directory = self.retired_submodule("dotbot")
        backup = self.home / ".zshrc.bak"
        backup.write_text("previous .zshrc")
        cache = self.repository / "__pycache__"
        cache.mkdir()
        arguments = [
            "clean_obsolete.py",
            "--root",
            str(self.home),
            "--repository",
            str(self.repository),
            "--dry-run",
        ]

        with (
            patch.object(
                clean.managed, "load_configuration", return_value=self.config()
            ),
            patch("sys.argv", arguments),
            patch("builtins.input", side_effect=self.fail),
            patch("sys.stdout"),
        ):
            self.assertEqual(clean.main(), 0)

        self.assertEqual(backup.read_text(), "previous .zshrc")
        self.assertTrue(git_directory.is_dir())
        self.assertTrue(cache.is_dir())

    def test_keeps_submodules_still_declared(self):
        self.retired_submodule("dotbot")
        (self.repository / ".gitmodules").write_text(
            '[submodule "dotbot"]\n\tpath = dotbot\n\turl = x\n'
        )

        plan = self.plan()
        self.assertTrue(plan.is_empty())

    def test_lists_caches_and_untracked_broken_links(self):
        cache = self.repository / "scripts" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "x.pyc").write_bytes(b"")
        untracked = self.repository / "dangling"
        untracked.symlink_to("/nonexistent")
        tracked = self.repository / "tracked-link"
        tracked.symlink_to("/nonexistent")
        git(self.repository, "add", "tracked-link")
        skipped = self.repository / ".claude" / "worktrees" / "x" / "__pycache__"
        skipped.mkdir(parents=True)

        plan = clean.Plan()
        clean.repository_files(self.repository, plan)

        self.assertEqual(sorted(plan.paths), sorted([cache, untracked]))
        self.assertEqual(len(plan.kept), 1)
        self.assertIn("tracked by Git", plan.kept[0])

        clean.apply(plan, self.repository)
        self.assertFalse(cache.exists())
        self.assertFalse(untracked.is_symlink())
        self.assertTrue(tracked.is_symlink())
        self.assertTrue(skipped.is_dir())

    def test_glob_named_link_is_not_matched_against_tracked_files(self):
        (self.repository / "ab").write_text("")
        git(self.repository, "add", "ab")
        link = self.repository / "a*"
        link.symlink_to("/nonexistent")

        plan = clean.Plan()
        clean.repository_files(self.repository, plan)

        self.assertEqual(plan.paths, [link])

    def test_leaves_nested_checkouts_and_virtualenvs_alone(self):
        nested = self.repository / "bundle" / "Vundle.vim"
        repository(nested)
        (nested / "dangling").symlink_to("/nonexistent")
        (nested / "__pycache__").mkdir()
        venv = self.repository / ".venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "pyvenv.cfg").write_text("home = /usr/bin\n")
        (venv / "bin" / "python").symlink_to("/nonexistent/python")

        plan = clean.Plan()
        clean.repository_files(self.repository, plan)

        self.assertEqual(plan.paths, [])


class MakefileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        shutil.copy(ROOT / "Makefile", self.work / "Makefile")
        playbook = self.work / "ansible-playbook"
        playbook.write_text(
            "#!/bin/sh\n"
            "echo 'ansible-playbook [core 2.22.0]'\n"
            "echo '  python version = 3.14.0 (main) [GCC] (/opt/ansible/bin/python)'\n"
        )
        playbook.chmod(0o755)
        self.playbook = playbook

    def make(self, *arguments):
        return subprocess.run(
            ["make", "-n", f"ANSIBLE_PLAYBOOK={self.playbook}", *arguments],
            cwd=self.work,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={**os.environ, "DRY_RUN": ""},
        )

    def test_clean_runs_with_the_interpreter_of_ansible(self):
        result = self.make("clean")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            '"/opt/ansible/bin/python" scripts/clean_obsolete.py', result.stdout
        )

    def test_dry_run_takes_only_zero_or_one(self):
        self.assertIn("--dry-run", self.make("clean", "DRY_RUN=1").stdout)
        self.assertNotIn("--dry-run", self.make("clean", "DRY_RUN=0").stdout)
        refused = self.make("clean", "DRY_RUN=yes")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("DRY_RUN=yes is not 0 or 1", refused.stderr)


if __name__ == "__main__":
    unittest.main()
