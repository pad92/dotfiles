import hashlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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
            **{
                name: templar.template(variables[name])
                for name in managed.PATH_VARIABLES
            },
            "audio_config_home": str(self.home / ".config"),
            "audio_obsolete_files": {},
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

    def test_lists_a_managed_file_that_is_a_broken_link(self):
        zshrc = self.link(".zshrc", "../.dotfiles/zshrc")

        self.assertEqual(clean.home_broken_links(self.home, self.config()), [zshrc])


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

    def test_end_of_input_at_the_prompt_keeps_the_backups(self):
        backup = self.backup()
        plan = clean.Plan(backups=[backup])

        def closed_input(_):
            raise EOFError

        with redirect_stdout(io.StringIO()):
            clean.confirm_removal(plan, prompt=closed_input, interactive=True)
        clean.apply(plan, self.home)

        self.assertTrue(backup.exists())
        self.assertIn("not confirmed", plan.kept[0])

    def test_terminal_is_detected_from_standard_input(self):
        backup = self.backup()
        plan = clean.Plan(backups=[backup])

        with (
            patch("sys.stdin.isatty", return_value=False),
            redirect_stdout(io.StringIO()),
        ):
            clean.confirm_removal(plan, prompt=self.fail)

        self.assertIn("no terminal", plan.kept[0])

    def test_nothing_to_confirm_does_not_prompt(self):
        plan = clean.Plan(paths=[self.home / "__pycache__"])

        clean.confirm_removal(plan, prompt=self.fail, interactive=True)

        self.assertEqual(plan.kept, [])

    def test_paths_gone_or_repaired_before_apply_are_left_alone(self):
        vanished_backup = self.home / ".zshrc.bak"
        vanished_cache = self.home / "__pycache__"
        repaired = self.link(".vimrc", str(self.root / "vimrc"))
        plan = clean.Plan(backups=[vanished_backup], paths=[vanished_cache, repaired])
        (self.root / "vimrc").write_text("")

        clean.apply(plan, self.home)

        self.assertTrue(repaired.is_symlink())


class ObsoleteFileTests(HomeTestCase):
    SHIPPED = b"context.properties = {}\n"
    RELATIVE = "pipewire/pipewire.conf.d/10-realtime.conf"

    def configuration(self):
        return {
            **self.config(),
            "audio_obsolete_files": {
                self.RELATIVE: hashlib.sha1(self.SHIPPED).hexdigest()
            },
        }

    def obsolete(self, content: bytes = SHIPPED) -> Path:
        path = self.home / ".config" / self.RELATIVE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def plan(self):
        plan = clean.Plan()
        clean.role_obsolete_files(self.configuration(), plan)
        return plan

    def test_unchanged_obsolete_file_is_removed_without_confirmation(self):
        path = self.obsolete()
        plan = self.plan()

        self.assertEqual(list(plan.obsolete_files), [path])
        self.assertFalse(plan.needs_confirmation())
        clean.confirm_removal(plan, prompt=self.fail, interactive=False)
        clean.apply(plan, self.home)

        self.assertFalse(path.exists())
        self.assertTrue(path.parent.is_dir())

    def test_changed_obsolete_file_is_kept_and_reported(self):
        path = self.obsolete(b"context.properties = { mine = true }\n")
        plan = self.plan()

        self.assertEqual(plan.obsolete_files, {})
        self.assertEqual(plan.kept, [f"{path}: obsolete file that was changed by hand"])

    def test_obsolete_path_that_is_a_link_is_kept(self):
        target = self.root / "shared.conf"
        target.write_bytes(self.SHIPPED)
        path = self.home / ".config" / self.RELATIVE
        path.parent.mkdir(parents=True)
        path.symlink_to(target)

        plan = self.plan()

        self.assertEqual(plan.obsolete_files, {})
        self.assertEqual(
            plan.kept, [f"{path}: obsolete file that is not a regular file"]
        )

    def test_missing_obsolete_file_is_not_listed(self):
        plan = self.plan()

        self.assertTrue(plan.is_empty())
        self.assertEqual(plan.kept, [])

    def test_linked_parent_directory_is_not_followed(self):
        outside = self.root / "outside/pipewire.conf.d"
        outside.mkdir(parents=True)
        (outside / "10-realtime.conf").write_bytes(self.SHIPPED)
        (self.home / ".config/pipewire").mkdir(parents=True)
        (self.home / ".config/pipewire/pipewire.conf.d").symlink_to(outside)

        plan = self.plan()

        self.assertEqual(plan.obsolete_files, {})
        self.assertTrue((outside / "10-realtime.conf").exists())

    def test_file_edited_after_the_plan_is_left_alone(self):
        path = self.obsolete()
        plan = self.plan()
        path.write_bytes(b"edited meanwhile\n")

        clean.apply(plan, self.home)

        self.assertEqual(path.read_bytes(), b"edited meanwhile\n")

    def test_report_names_the_obsolete_file(self):
        path = self.obsolete()
        output = io.StringIO()
        with redirect_stdout(output):
            clean.report(self.plan(), dry_run=True)

        self.assertEqual(
            output.getvalue().splitlines(), [f"would remove obsolete file {path}"]
        )

    def test_escaping_obsolete_path_is_rejected(self):
        configuration = {
            **self.config(),
            "audio_obsolete_files": {"../outside.conf": "0" * 40},
        }

        with self.assertRaises(ValueError):
            clean.role_obsolete_files(configuration, clean.Plan())


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

    def test_clone_with_its_checkout_still_present_is_kept(self):
        git_directory = self.retired_submodule("dotbot")
        config = str(git_directory / "config")
        worktree = git(self.root, "config", "--file", config, "core.worktree")
        checkout = (git_directory / worktree).resolve()
        checkout.mkdir(parents=True)
        (checkout / "install").write_text("")

        plan = self.plan()

        self.assertEqual(plan.submodule_directories, [])
        self.assertIn("still exists", plan.kept[0])

    def test_clone_without_a_worktree_setting_is_removed(self):
        git_directory = self.retired_submodule("dotbot")
        config = str(git_directory / "config")
        git(self.root, "config", "--file", config, "--unset", "core.worktree")

        plan = self.plan()

        self.assertEqual(plan.submodule_directories, [git_directory.resolve()])

    def test_unreadable_clone_is_kept(self):
        git_directory = self.retired_submodule("dotbot")
        shutil.rmtree(git_directory / "objects")
        (git_directory / "objects").mkdir()

        plan = self.plan()

        self.assertEqual(plan.submodule_directories, [])
        self.assertIn("Git cannot read", plan.kept[0])

    def test_section_whose_name_leaves_git_modules_is_kept(self):
        git(self.repository, "config", "submodule.../../escape.url", "x")

        plan = self.plan()

        self.assertEqual(plan.submodule_sections, [])
        self.assertIn("leaves .git/modules", plan.kept[0])

    def test_linked_worktree_leaves_submodules_to_the_main_one(self):
        self.retired_submodule("dotbot")
        worktree = self.root / "linked"
        git(self.repository, "worktree", "add", "-q", str(worktree))

        plan = clean.Plan()
        clean.submodule_leftovers(worktree, plan)

        self.assertEqual(plan.submodule_sections, [])
        self.assertIn("main worktree", plan.kept[0])

    def test_removing_one_clone_keeps_its_sibling_and_their_parent(self):
        removed = self.retired_submodule("zsh/plugins/a")
        kept = self.retired_submodule("zsh/plugins/b", local_commit=True)

        clean.apply(self.plan(), self.repository)

        self.assertFalse(removed.exists())
        self.assertTrue(kept.is_dir())

    def test_section_already_gone_at_apply_stops_the_removal(self):
        self.retired_submodule("dotbot")
        plan = self.plan()
        git(self.repository, "config", "--remove-section", "submodule.dotbot")

        with self.assertRaisesRegex(RuntimeError, "submodule.dotbot"):
            clean.apply(plan, self.repository)

    def test_git_failures_stop_with_an_error(self):
        not_a_repository = self.root / "plain"
        not_a_repository.mkdir()
        (not_a_repository / "config").write_text("[broken\n")
        (not_a_repository / ".gitmodules").write_text("[broken\n")

        self.assertFalse(clean.is_main_worktree(not_a_repository))
        with self.assertRaisesRegex(RuntimeError, "not a Git repository"):
            clean.git_common_directory(not_a_repository)
        with self.assertRaisesRegex(RuntimeError, "submodules of the Git config"):
            clean.configured_submodules(not_a_repository)
        with self.assertRaisesRegex(RuntimeError, ".gitmodules"):
            clean.declared_submodules(not_a_repository)
        with self.assertRaisesRegex(RuntimeError, "prunable worktrees"):
            clean.prunable_worktrees(not_a_repository)
        with self.assertRaisesRegex(RuntimeError, "worktree prune failed"):
            clean.apply(clean.Plan(prunable_worktrees=["x"]), not_a_repository)

    def test_report_lists_every_kind_of_item(self):
        plan = clean.Plan(
            backups=[Path("/h/.zshrc.bak")],
            paths=[Path("/h/link")],
            submodule_sections=["dotbot"],
            submodule_directories=[Path("/r/.git/modules/dotbot")],
            prunable_worktrees=["Removing worktrees/gone"],
            kept=["submodule vim: reason"],
        )
        output = io.StringIO()

        with redirect_stdout(output):
            clean.report(plan, dry_run=False)
            clean.report(clean.Plan(), dry_run=True)

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "remove backup /h/.zshrc.bak",
                "remove /h/link",
                "remove /r/.git/modules/dotbot",
                'remove [submodule "dotbot"] from the Git config',
                "remove worktree record: Removing worktrees/gone",
                "keep submodule vim: reason",
                "Nothing to clean.",
            ],
        )

    def main(self, *options: str, repository: Path | None = None) -> int:
        arguments = [
            "clean_obsolete.py",
            "--root",
            str(self.home),
            "--repository",
            str(repository or self.repository),
            *options,
        ]
        with (
            patch.object(
                clean.managed, "load_configuration", return_value=self.config()
            ),
            patch("sys.argv", arguments),
            patch("sys.stdin.isatty", return_value=False),
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()) as errors,
        ):
            status = clean.main()
        self.errors = errors.getvalue()
        return status

    def test_run_without_a_terminal_removes_caches_and_keeps_backups(self):
        backup = self.home / ".zshrc.bak"
        backup.write_text("previous .zshrc")
        cache = self.repository / "__pycache__"
        cache.mkdir()

        self.assertEqual(self.main(), 0)

        self.assertEqual(backup.read_text(), "previous .zshrc")
        self.assertFalse(cache.exists())

    def test_run_outside_a_repository_stops_with_an_error(self):
        plain = self.root / "plain"
        plain.mkdir()

        self.assertEqual(self.main(repository=plain), 1)
        self.assertIn("clean stopped", self.errors)

    def test_home_must_be_a_directory(self):
        self.home.rmdir()

        with self.assertRaises(SystemExit) as raised:
            self.main()
        self.assertEqual(raised.exception.code, 2)

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
