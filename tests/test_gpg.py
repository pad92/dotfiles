"""Exercise the Vault-driven gpg role against a throwaway home directory."""

import re
import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

from vault_role import RolePlayMixin, load_role, site_entries

ROLE = load_role("gpg")
HANDLER = "Reload the GnuPG daemons"
# RFC 6761 name: never a real mailbox.
EMAIL = "test-user@example.invalid"
PASSPHRASE = "fixture-passphrase"
GPG = shutil.which("gpg") or ""
SAMPLE = ROLE["path"] / "vault_gpg.sample.yml"


def load_sample():
    return yaml.safe_load(SAMPLE.read_text())


def gpg(home: Path, *args: str, stdin: str | None = None) -> str:
    result = subprocess.run(
        [GPG, "--homedir", str(home), "--batch", *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return result.stdout


def fingerprints(listing: str) -> list[str]:
    return [
        line.split(":")[9] for line in listing.splitlines() if line.startswith("fpr:")
    ]


def agent_pid(home: Path) -> str:
    """The pid of the gpg-agent of home, started on demand."""
    result = subprocess.run(
        ["gpg-connect-agent", "--homedir", str(home), "getinfo pid", "/bye"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return next(line for line in result.stdout.splitlines() if line.startswith("D "))


def stop_agents(home: Path):
    """gpg starts an agent per home directory; stop it with the test."""
    if home.exists():
        subprocess.run(
            ["gpgconf", "--homedir", str(home), "--kill", "all"],
            capture_output=True,
            timeout=30,
            check=False,
        )


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class GpgTaskTests(RolePlayMixin, unittest.TestCase):
    role = ROLE
    home_variable = "gpg_home"

    def setUp(self):
        super().setUp()
        self.gnupg = self.home / ".gnupg"
        if GPG:
            self.addCleanup(stop_agents, self.gnupg)

    def make_gpg_key(self, name: str, passphrase: str = PASSPHRASE):
        """A key generated in its own home, exported as the vault would hold it."""
        source = self.work / f"source-{name}"
        source.mkdir(mode=0o700)
        self.addCleanup(stop_agents, source)
        gpg(
            source,
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            passphrase,
            "--quick-gen-key",
            f"{name} <{EMAIL}>",
            "ed25519",
            "sign",
            "never",
        )
        fingerprint = fingerprints(gpg(source, "--with-colons", "--list-secret-keys"))[
            0
        ]
        secret = gpg(
            source,
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            passphrase,
            "--armor",
            "--export-secret-keys",
            fingerprint,
        )
        public = gpg(source, "--armor", "--export", fingerprint)
        return fingerprint, secret, public

    # --- Inert without its vault ---------------------------------------------

    def test_without_vault_nothing_is_created(self):
        output = self.run_play({})
        self.assertIn("GnuPG skipped", output)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_ssh_vault_alone_does_not_wake_the_gpg_role(self):
        output = self.run_play(
            {
                "vault_ssh_config_options": {"ForwardAgent": False},
                "vault_ssh_keys": [{"name": "id"}],
            }
        )
        self.assertIn("GnuPG skipped", output)
        self.assertEqual(list(self.home.iterdir()), [])

    # --- Keys and configuration ----------------------------------------------

    @unittest.skipUnless(GPG, "requires gpg")
    def test_protected_secret_key_is_imported_once_with_its_trust(self):
        fingerprint, secret, _public = self.make_gpg_key("primary")
        settings = {
            "vault_gpg_config": {"common.conf": ["use-keyboxd"], "gpg.conf": ["armor"]},
            "vault_gpg_keys": [
                {"fingerprint": fingerprint, "armor": secret, "trust": "ultimate"}
            ],
        }
        first = self.run_play(settings)
        self.assertEqual(self.gnupg.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.gnupg / "common.conf").stat().st_mode & 0o777, 0o600)
        self.assertIn("use-keyboxd\n", (self.gnupg / "common.conf").read_text())
        self.assertIn(f"RUNNING HANDLER [{HANDLER}]", first)
        self.assertIn(
            fingerprint,
            fingerprints(gpg(self.gnupg, "--with-colons", "--list-secret-keys")),
        )
        self.assertIn(
            f"{fingerprint}:6:", gpg(self.gnupg, "--export-ownertrust").splitlines()
        )
        # The key keeps its passphrase: an empty one cannot sign with it.
        unlocked = subprocess.run(
            [
                GPG,
                "--homedir",
                str(self.gnupg),
                "--batch",
                "--pinentry-mode",
                "loopback",
                "--passphrase",
                "",
                "--local-user",
                fingerprint,
                "--clearsign",
            ],
            input="x",
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertNotEqual(unlocked.returncode, 0)

        second = self.run_play(settings)
        self.assertIn("changed=0", second)
        self.assertNotIn(f"RUNNING HANDLER [{HANDLER}]", second)

    @unittest.skipUnless(GPG, "requires gpg")
    def test_trust_change_is_applied_to_a_key_already_present(self):
        fingerprint, _secret, public = self.make_gpg_key("peer")
        key = {"fingerprint": fingerprint, "armor": public, "trust": "marginal"}
        self.run_play({"vault_gpg_keys": [key]})
        self.assertFalse(
            fingerprints(gpg(self.gnupg, "--with-colons", "--list-secret-keys"))
        )
        self.assertIn(
            f"{fingerprint}:4:", gpg(self.gnupg, "--export-ownertrust").splitlines()
        )
        output = self.run_play({"vault_gpg_keys": [{**key, "trust": "full"}]})
        self.assertIn("changed=1", output)
        self.assertIn(
            f"{fingerprint}:5:", gpg(self.gnupg, "--export-ownertrust").splitlines()
        )

    @unittest.skipUnless(GPG, "requires gpg")
    def test_armor_of_another_key_fails_instead_of_importing_on_every_run(self):
        expected, _secret, _public = self.make_gpg_key("expected")
        _other, _secret, other_public = self.make_gpg_key("other")
        output = self.run_play(
            {"vault_gpg_keys": [{"fingerprint": expected, "armor": other_public}]},
            succeed=False,
        )
        self.assertIn("positions 0", " ".join(output.split()))
        self.assertIn(
            "the armor does not hold the key of the fingerprint",
            " ".join(output.split()),
        )

    @unittest.skipUnless(
        GPG and shutil.which("gpg-connect-agent"), "requires gpg-connect-agent"
    )
    def test_common_conf_change_restarts_the_agent_other_files_reload_it(self):
        # common.conf (use-keyboxd...) is read only at start: a reload is not
        # enough, the daemons must stop so the import already uses it.
        self.run_play({"vault_gpg_config": {"gpg.conf": ["armor"]}})
        before = agent_pid(self.gnupg)
        self.run_play({"vault_gpg_config": {"gpg.conf": ["armor", "no-greeting"]}})
        self.assertEqual(agent_pid(self.gnupg), before)
        self.run_play(
            {
                "vault_gpg_config": {
                    "gpg.conf": ["armor", "no-greeting"],
                    "common.conf": ["use-keyboxd"],
                }
            }
        )
        self.assertNotEqual(agent_pid(self.gnupg), before)

    # --- Check mode ------------------------------------------------------------

    @unittest.skipUnless(GPG, "requires gpg")
    def test_check_mode_on_a_fresh_home_succeeds_and_writes_nothing(self):
        # make check runs the playbook with --check before the first deploy:
        # gpg itself would create ~/.gnupg if the role ran it.
        fingerprint, secret, _public = self.make_gpg_key("fresh")
        self.run_play(
            {
                "vault_gpg_config": {"gpg.conf": ["armor"]},
                "vault_gpg_keys": [
                    {"fingerprint": fingerprint, "armor": secret, "trust": "ultimate"}
                ],
            },
            extra=("--check",),
        )
        self.assertEqual(list(self.home.iterdir()), [])

    @unittest.skipUnless(GPG, "requires gpg")
    def test_check_mode_on_a_deployed_keyring_succeeds_and_changes_nothing(self):
        fingerprint, _secret, public = self.make_gpg_key("deployed")
        key = {"fingerprint": fingerprint, "armor": public, "trust": "marginal"}
        self.run_play({"vault_gpg_keys": [key]})
        self.run_play(
            {"vault_gpg_keys": [{**key, "trust": "full"}]}, extra=("--check",)
        )
        self.assertIn(
            f"{fingerprint}:4:", gpg(self.gnupg, "--export-ownertrust").splitlines()
        )

    # --- Validation ----------------------------------------------------------

    def test_values_that_could_inject_lines_or_paths_are_refused(self):
        valid_fpr = "A" * 40
        armor = "-----BEGIN PGP PUBLIC KEY BLOCK-----\n\nxx\n-----END PGP PUBLIC KEY BLOCK-----\n"
        for overrides in [
            {"vault_gpg_config": {"../gpg.conf": ["armor"]}},
            {"vault_gpg_config": {"gpg.conf": "armor"}},
            {"vault_gpg_config": {"gpg.conf": ["armor\nkeyserver x"]}},
            {"vault_gpg_keys": [{"fingerprint": valid_fpr.lower(), "armor": armor}]},
            {"vault_gpg_keys": [{"fingerprint": "A" * 16, "armor": armor}]},
            {"vault_gpg_keys": [{"fingerprint": valid_fpr, "armor": "not a key"}]},
            {
                "vault_gpg_keys": [
                    {"fingerprint": valid_fpr, "armor": armor, "trust": "total"}
                ]
            },
        ]:
            with self.subTest(overrides=overrides):
                output = self.run_play(overrides, succeed=False)
                self.assertIn("Invalid GnuPG settings", output)
                self.assertEqual(list(self.home.iterdir()), [])

    # --- Sample vault ----------------------------------------------------------

    def test_sample_as_shipped_is_refused(self):
        # A copy encrypted without its placeholders replaced must not deploy.
        output = self.run_play(load_sample(), succeed=False)
        self.assertIn("Invalid GnuPG settings", output)
        self.assertEqual(list(self.home.iterdir()), [])

    @unittest.skipUnless(GPG, "requires gpg")
    def test_sample_filled_with_a_real_key_deploys(self):
        sample = load_sample()
        fingerprint, secret, _public = self.make_gpg_key("sample")
        for key in sample["vault_gpg_keys"]:
            key.update(fingerprint=fingerprint, armor=secret)
        self.run_play(sample)
        for name, lines in sample["vault_gpg_config"].items():
            with self.subTest(name=name):
                body = (self.gnupg / name).read_text().splitlines()
                self.assertEqual(
                    [line for line in body if not line.startswith("#")], lines
                )
        self.assertIn(
            fingerprint,
            fingerprints(gpg(self.gnupg, "--with-colons", "--list-secret-keys")),
        )
        self.assertIn(
            f"{fingerprint}:6:", gpg(self.gnupg, "--export-ownertrust").splitlines()
        )
        self.assertIn("changed=0", self.run_play(sample))

    # --- Secrets stay out of the output --------------------------------------

    @unittest.skipUnless(GPG, "requires gpg")
    def test_vault_values_never_reach_the_output_even_with_diff_and_verbose(self):
        fingerprint, secret, _public = self.make_gpg_key("hidden")
        output = self.run_play(
            {
                "vault_gpg_config": {"gpg.conf": [f"default-key {EMAIL}"]},
                "vault_gpg_keys": [
                    {"fingerprint": fingerprint, "armor": secret, "trust": "ultimate"}
                ],
            },
            extra=("--diff", "-vv"),
        )
        # The play variables are dumped only in the play file, never printed.
        for marker in [
            "PGP PRIVATE KEY BLOCK",
            secret.splitlines()[3],
            EMAIL,
            "default-key",
        ]:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, output)


class GpgRepositoryContractTests(unittest.TestCase):
    """The role ships no personal data: everything comes from the vault."""

    def test_role_files_hold_no_key_or_address(self):
        email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")
        key = re.compile(r"-----BEGIN [A-Z ]*(PRIVATE|PUBLIC) KEY|\b[0-9A-F]{40}\b")
        for path in sorted(p for p in ROLE["path"].rglob("*") if p.is_file()):
            text = path.read_text()
            with self.subTest(path=path.name):
                self.assertIsNone(email.search(text))
                self.assertIsNone(key.search(text))

    def test_every_personal_default_reads_the_vault(self):
        defaults = ROLE["defaults"]
        for name in ["gpg_config", "gpg_keys"]:
            with self.subTest(name=name):
                self.assertRegex(
                    defaults[name],
                    rf"^\{{\{{ vault_{name} \| default\((\{{\}}|\[\])\) \}}\}}$",
                )
        self.assertIs(defaults["gpg_no_log"], True)

    def test_sample_documents_exactly_the_vault_variables_of_the_role(self):
        read = {
            match
            for value in ROLE["defaults"].values()
            for match in re.findall(r"\bvault_gpg_\w+", str(value))
        }
        self.assertEqual(set(load_sample()), read)

    def test_site_runs_the_role_as_the_user(self):
        entries = site_entries("gpg")
        self.assertEqual(len(entries), 1)
        self.assertIs(entries[0]["become"], False)
        self.assertEqual(entries[0]["tags"], ["dotfiles", "gpg"])


if __name__ == "__main__":
    unittest.main()
