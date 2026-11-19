"""Exercise the Vault-driven ssh role against a throwaway home directory."""

import re
import shutil
import subprocess
import unittest

import yaml

from vault_role import RolePlayMixin, load_role, site_entries

ROLE = load_role("ssh")
# RFC 6761 names: never a real host or mailbox.
HOST = "bastion.example.test"
EMAIL = "test-user@example.invalid"
# Split so that the detect-private-key hook does not take the fixture for a
# real key; the joined string is the header the role looks for.
FAKE_PRIVATE = (
    "-----BEGIN OPENSSH "
    "PRIVATE KEY-----\n"
    "ZmFrZS1wcml2YXRlLWtleS1tYXJrZXI=\n"
    "-----END OPENSSH PRIVATE KEY-----\n"
)
FAKE_PUBLIC = f"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakePublicKeyMarker {EMAIL}"
HOST_KEY = f"{HOST} ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeHostKeyMarker"
SSH = shutil.which("ssh") or ""
SSH_KEYGEN = shutil.which("ssh-keygen") or ""
SAMPLE = ROLE["path"] / "vault_ssh.sample.yml"


def load_sample():
    return yaml.safe_load(SAMPLE.read_text())


def ssh_settings():
    return {
        "vault_ssh_config_options": {
            "ForwardAgent": False,
            "ServerAliveInterval": 10,
            "SetEnv": ["TERM=xterm-256color", "LC_FIXTURE=1"],
        },
        "vault_ssh_config_fragments": {
            "bastion": f"Host bastion\n    HostName {HOST}\n    ForwardAgent yes\n",
        },
    }


def ssh_keys():
    return {
        "vault_ssh_keys": [
            {"name": "id_fixture", "private": FAKE_PRIVATE, "public": FAKE_PUBLIC}
        ],
        "vault_ssh_authorized_keys": [FAKE_PUBLIC],
        "vault_ssh_known_hosts": [{"name": HOST, "key": HOST_KEY}],
    }


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class SshTaskTests(RolePlayMixin, unittest.TestCase):
    role = ROLE
    home_variable = "ssh_home"

    def setUp(self):
        super().setUp()
        self.ssh = self.home / ".ssh"

    # --- Inert without its vault ---------------------------------------------

    def test_without_vault_nothing_is_created(self):
        output = self.run_play({})
        self.assertIn("SSH skipped", output)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_gnupg_vault_alone_does_not_wake_the_ssh_role(self):
        output = self.run_play(
            {
                "vault_gpg_config": {"gpg.conf": ["armor"]},
                "vault_gpg_keys": [{"fingerprint": "A" * 40}],
            }
        )
        self.assertIn("SSH skipped", output)
        self.assertEqual(list(self.home.iterdir()), [])

    # --- Configuration -------------------------------------------------------

    def test_ssh_config_renders_host_star_after_the_included_fragments(self):
        self.run_play(ssh_settings())
        config = (self.ssh / "config").read_text()
        body = [
            line for line in config.splitlines() if line and not line.startswith("#")
        ]
        self.assertEqual(
            body,
            [
                f"Include {self.ssh}/config.d/*",
                "Host *",
                "    ForwardAgent no",
                "    ServerAliveInterval 10",
                "    SetEnv TERM=xterm-256color",
                "    SetEnv LC_FIXTURE=1",
            ],
        )
        fragment = self.ssh / "config.d/bastion"
        self.assertEqual(
            fragment.read_text(),
            f"Host bastion\n    HostName {HOST}\n    ForwardAgent yes\n",
        )
        for path, mode in [
            (self.ssh, 0o700),
            (self.ssh / "config.d", 0o700),
            (self.ssh / "sockets", 0o700),
            (self.ssh / "config", 0o600),
            (fragment, 0o600),
        ]:
            with self.subTest(path=path.name):
                self.assertEqual(path.stat().st_mode & 0o777, mode)

    @unittest.skipUnless(SSH, "requires the OpenSSH client")
    def test_openssh_reads_the_fragment_before_host_star(self):
        self.run_play(ssh_settings())
        resolved = subprocess.run(
            [SSH, "-G", "-F", str(self.ssh / "config"), "bastion"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.splitlines()
        self.assertIn(f"hostname {HOST}", resolved)
        # The per-host value wins over "Host *": the order matters.
        self.assertIn("forwardagent yes", resolved)
        other = subprocess.run(
            [SSH, "-G", "-F", str(self.ssh / "config"), "other.example.test"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.splitlines()
        self.assertIn("forwardagent no", other)

    @unittest.skipUnless(SSH, "requires the OpenSSH client")
    def test_openssh_rejects_an_invalid_fragment_before_it_is_written(self):
        settings = ssh_settings()
        settings["vault_ssh_config_fragments"] = {
            "broken": "Host x\n    NotAnOption yes\n"
        }
        self.run_play(settings, succeed=False)
        self.assertFalse((self.ssh / "config.d/broken").exists())
        self.assertFalse((self.ssh / "config").exists())

    def test_unlisted_fragments_stay_unless_the_purge_is_requested(self):
        (self.ssh / "config.d").mkdir(parents=True, mode=0o700)
        manual = self.ssh / "config.d/manual"
        manual.write_text("Host manual\n")
        self.run_play(ssh_settings())
        self.assertTrue(manual.exists())

        self.run_play({**ssh_settings(), "ssh_config_fragments_exclusive": True})
        self.assertFalse(manual.exists())
        self.assertTrue((self.ssh / "config.d/bastion").exists())

    def test_purge_keeps_directories_and_hidden_files_of_config_d(self):
        # The purge deletes only regular fragments: a directory is never
        # removed with its content, and OpenSSH's * skips hidden files.
        nested = self.ssh / "config.d/tool/state"
        nested.parent.mkdir(parents=True, mode=0o700)
        nested.write_text("kept\n")
        hidden = self.ssh / "config.d/.keep"
        hidden.write_text("")
        self.run_play({**ssh_settings(), "ssh_config_fragments_exclusive": True})
        self.assertTrue(nested.is_file())
        self.assertEqual(nested.read_text(), "kept\n")
        self.assertTrue(hidden.exists())

    # --- Keys ----------------------------------------------------------------

    @unittest.skipUnless(SSH_KEYGEN, "known_hosts requires ssh-keygen")
    def test_keys_and_authorized_keys_are_written_with_private_modes(self):
        self.ssh.mkdir(mode=0o700)
        learnt = "learnt.example.test ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILearntKey\n"
        (self.ssh / "known_hosts").write_text(learnt)
        settings = ssh_keys()
        settings["vault_ssh_keys"].append(
            {"name": "id_agentless", "private": FAKE_PRIVATE}
        )
        self.run_play(settings)
        self.assertEqual((self.ssh / "id_fixture").read_text(), FAKE_PRIVATE)
        self.assertEqual((self.ssh / "id_fixture").stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.ssh / "id_fixture.pub").read_text(), FAKE_PUBLIC + "\n")
        self.assertEqual((self.ssh / "id_fixture.pub").stat().st_mode & 0o777, 0o644)
        self.assertFalse((self.ssh / "id_agentless.pub").exists())
        authorized = self.ssh / "authorized_keys"
        self.assertEqual(
            [
                line
                for line in authorized.read_text().splitlines()
                if not line.startswith("#")
            ],
            [FAKE_PUBLIC],
        )
        self.assertEqual(authorized.stat().st_mode & 0o777, 0o600)
        # The pinned key is added; the one ssh learnt stays.
        self.assertEqual(
            (self.ssh / "known_hosts").read_text().splitlines(),
            [learnt.strip(), HOST_KEY],
        )
        # Keys only: the role does not take over ~/.ssh/config.
        self.assertFalse((self.ssh / "config").exists())

    @unittest.skipUnless(SSH_KEYGEN, "known_hosts requires ssh-keygen")
    def test_second_run_changes_nothing(self):
        settings = {**ssh_settings(), **ssh_keys()}
        self.run_play(settings)
        self.assertIn("changed=0", self.run_play(settings))

    # --- Validation ----------------------------------------------------------

    def test_values_that_could_inject_lines_or_paths_are_refused(self):
        for overrides in [
            {
                "vault_ssh_config_options": {
                    "ForwardAgent": "no\nHost *\n    ProxyCommand x"
                }
            },
            {"vault_ssh_config_options": {"Forward Agent": "no"}},
            {"vault_ssh_config_options": {"SetEnv": ["A=1\nProxyCommand x"]}},
            {"vault_ssh_config_options": "ForwardAgent no"},
            {"vault_ssh_config_fragments": {"../config": "Host x\n"}},
            {"vault_ssh_config_fragments": {".hidden": "Host x\n"}},
            {"vault_ssh_authorized_keys": [f"{FAKE_PUBLIC}\n{FAKE_PUBLIC}"]},
            {"vault_ssh_authorized_keys": FAKE_PUBLIC},
            {"vault_ssh_known_hosts": [{"name": HOST}]},
            {"vault_ssh_keys": [{"name": "config", "private": FAKE_PRIVATE}]},
            {"vault_ssh_keys": [{"name": "id.pub", "private": FAKE_PRIVATE}]},
            {"vault_ssh_keys": [{"name": "../id", "private": FAKE_PRIVATE}]},
            {"vault_ssh_keys": [{"name": "id", "private": FAKE_PUBLIC}]},
            # A name the role creates as a directory (ssh_extra_dirs).
            {"vault_ssh_keys": [{"name": "sockets", "private": FAKE_PRIVATE}]},
            # Only scalars render as one option line.
            {"vault_ssh_config_options": {"SetEnv": [["A=1", "B=2"]]}},
            {"vault_ssh_config_options": {"ForwardAgent": None}},
            # Placeholders left from the sample: never written to ~/.ssh.
            {"vault_ssh_authorized_keys": ["<one public key line>"]},
            {
                "vault_ssh_keys": [
                    {"name": "id", "private": FAKE_PRIVATE, "public": "<line>"}
                ]
            },
            {"vault_ssh_keys": [{"name": "id", "private": FAKE_PRIVATE, "public": 1}]},
            {"vault_ssh_known_hosts": [{"name": HOST, "key": "<the line>"}]},
            {
                "vault_ssh_known_hosts": [
                    {"name": HOST, "key": f"{HOST_KEY}\n{HOST_KEY}"}
                ]
            },
        ]:
            with self.subTest(overrides=overrides):
                output = self.run_play(overrides, succeed=False)
                self.assertIn("Invalid SSH settings", output)
                self.assertEqual(list(self.home.iterdir()), [])

    # --- Sample vault ----------------------------------------------------------

    def test_sample_as_shipped_is_refused(self):
        # A copy encrypted without its placeholders replaced must not deploy.
        output = self.run_play(load_sample(), succeed=False)
        self.assertIn("Invalid SSH settings", output)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_sample_with_only_its_private_key_filled_is_refused(self):
        # The authorized_keys placeholder alone would replace every key
        # allowed to log in: it must stop the run before anything is written.
        sample = load_sample()
        for key in sample["vault_ssh_keys"]:
            key.update(private=FAKE_PRIVATE, public=FAKE_PUBLIC)
        output = self.run_play(sample, succeed=False)
        self.assertIn("Invalid SSH settings", output)
        self.assertEqual(list(self.home.iterdir()), [])

    # --- Check mode ------------------------------------------------------------

    @unittest.skipUnless(SSH_KEYGEN, "known_hosts requires ssh-keygen")
    def test_check_mode_on_a_fresh_home_succeeds_and_writes_nothing(self):
        # make check runs the playbook with --check before the first deploy.
        self.run_play({**ssh_settings(), **ssh_keys()}, extra=("--check",))
        self.assertEqual(list(self.home.iterdir()), [])

    @unittest.skipUnless(
        SSH and SSH_KEYGEN, "requires the OpenSSH client and ssh-keygen"
    )
    def test_sample_filled_with_real_keys_deploys_and_openssh_reads_it(self):
        sample = load_sample()
        source = self.work / "source"
        source.mkdir(mode=0o700)
        for key in sample["vault_ssh_keys"]:
            path = source / key["name"]
            subprocess.run(
                [
                    SSH_KEYGEN,
                    "-q",
                    "-t",
                    "ed25519",
                    "-N",
                    "",
                    "-C",
                    EMAIL,
                    "-f",
                    str(path),
                ],
                capture_output=True,
                timeout=30,
                check=True,
            )
            key["private"] = path.read_text()
            key["public"] = path.with_suffix(".pub").read_text().strip()
        public = sample["vault_ssh_keys"][0]["public"]
        sample["vault_ssh_authorized_keys"] = [public]
        for host in sample["vault_ssh_known_hosts"]:
            host["key"] = f"{host['name']} {' '.join(public.split()[:2])}"

        self.run_play(sample)
        for key in sample["vault_ssh_keys"]:
            self.assertEqual((self.ssh / key["name"]).read_text(), key["private"])
        for name in sample["vault_ssh_config_fragments"]:
            self.assertTrue((self.ssh / "config.d" / name).is_file())
        resolved = subprocess.run(
            [SSH, "-G", "-F", str(self.ssh / "config"), "bastion"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.splitlines()
        self.assertIn("hostname bastion.example.test", resolved)
        self.assertIn("controlmaster auto", resolved)
        self.assertIn("changed=0", self.run_play(sample))

    # --- Secrets stay out of the output --------------------------------------

    @unittest.skipUnless(SSH_KEYGEN, "known_hosts requires ssh-keygen")
    def test_vault_values_never_reach_the_output_even_with_diff_and_verbose(self):
        output = self.run_play(
            {**ssh_settings(), **ssh_keys()}, extra=("--diff", "-vv")
        )
        # The play variables are dumped only in the play file, never printed.
        for marker in [
            "ZmFrZS1wcml2YXRlLWtleS1tYXJrZXI",
            "OPENSSH PRIVATE KEY",
            "FakePublicKeyMarker",
            "FakeHostKeyMarker",
            EMAIL,
            HOST,
            "bastion",
        ]:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, output)


class SshRepositoryContractTests(unittest.TestCase):
    """The role ships no personal data: everything comes from the vault."""

    def test_role_files_hold_no_key_address_or_host(self):
        email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")
        key = re.compile(
            r"-----BEGIN [A-Z ]*(PRIVATE|PUBLIC) KEY|ssh-(ed25519|rsa|dss) AAAA|ecdsa-sha2"
        )
        for path in sorted(p for p in ROLE["path"].rglob("*") if p.is_file()):
            text = path.read_text()
            with self.subTest(path=path.name):
                self.assertIsNone(email.search(text))
                self.assertIsNone(key.search(text))

    def test_every_personal_default_reads_the_vault(self):
        defaults = ROLE["defaults"]
        for name in [
            "ssh_config_options",
            "ssh_config_fragments",
            "ssh_authorized_keys",
            "ssh_known_hosts",
            "ssh_keys",
        ]:
            with self.subTest(name=name):
                self.assertRegex(
                    defaults[name],
                    rf"^\{{\{{ vault_{name} \| default\((\{{\}}|\[\])\) \}}\}}$",
                )
        self.assertIs(defaults["ssh_no_log"], True)

    def test_sample_documents_exactly_the_vault_variables_of_the_role(self):
        read = {
            match
            for value in ROLE["defaults"].values()
            for match in re.findall(r"\bvault_ssh_\w+", str(value))
        }
        self.assertEqual(set(load_sample()), read)

    def test_site_runs_the_role_as_the_user(self):
        entries = site_entries("ssh")
        self.assertEqual(len(entries), 1)
        self.assertIs(entries[0]["become"], False)
        self.assertEqual(entries[0]["tags"], ["dotfiles", "ssh"])


if __name__ == "__main__":
    unittest.main()
