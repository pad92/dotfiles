-- ▄▀█ █▀▄▀█ █▀▄
-- █▀█ █░▀░█ █▄▀

-- AMD GPU Optimizations for PadsTower

hl.env("AMD_VULKAN_ICD", "RADV")
-- hl.env("VK_ICD_FILENAMES", "/usr/share/vulkan/icd.d/radeon_icd.x86_64.json")

-- hl.env("ENABLE_HDR_WSI", "1")
hl.env("AQ_DRM_DEVICES", "/dev/dri/card1")
