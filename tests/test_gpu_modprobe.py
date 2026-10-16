import unittest
from pathlib import Path

from jinja2 import Environment


TEMPLATE = (
    Path(__file__).parents[1]
    / "ansible/roles/system/templates/gpu-modprobe.conf.j2"
)


class GpuModprobeTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = Environment().from_string(TEMPLATE.read_text(encoding="utf-8"))

    def render(self, profile):
        return self.template.render(packages_selected_groups=[profile])

    def test_modern_profile_enables_rtd3_without_forcing_vram_backup(self):
        config = self.render("09_nvidia_modern")

        self.assertIn("NVreg_DynamicPowerManagement=0x01", config)
        self.assertIn("NVreg_InitializeSystemMemoryAllocations=1", config)
        self.assertIn("options nvidia_drm modeset=1", config)
        self.assertNotIn("NVreg_PreserveVideoMemoryAllocations=1", config)
        self.assertNotIn("NVreg_UseKernelSuspendNotifiers=1", config)

    def test_legacy_profile_omits_modern_rtd3_options(self):
        config = self.render("09_nvidia_legacy")

        self.assertNotIn("NVreg_DynamicPowerManagement", config)
        self.assertNotIn("NVreg_UseKernelSuspendNotifiers", config)
        self.assertIn("NVreg_InitializeSystemMemoryAllocations=1", config)
        self.assertIn("options nvidia_drm modeset=1", config)


if __name__ == "__main__":
    unittest.main()
