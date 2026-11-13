import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from git_fixtures import git, repository

SCRIPTS = Path(__file__).parents[1] / "scripts"
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

        clean.confirm_backup_removal(plan, prompt=self.fail, interactive=False)
        clean.apply(plan, self.home)

        self.assertEqual(backup.read_text(), "previous .zshrc")
        self.assertIn("no terminal", plan.kept[0])

    def test_backups_are_kept_unless_remove_is_typed(self):
        backup = self.backup()
        plan = clean.Plan(backups=[backup])

        clean.confirm_backup_removal(plan, prompt=lambda _: "yes", interactive=True)
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

        clean.confirm_backup_removal(
            plan, prompt=lambda _: "REMOVE\n", interactive=True
        )
        clean.apply(plan, self.home)

        self.assertFalse(backup.exists())
        self.assertFalse(tree.exists())
        self.assertFalse(link.is_symlink())
        self.assertEqual(target.read_text(), "kept")


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
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


if __name__ == "__main__":
    unittest.main()
