local cooldown = 2 * 24 * 60 * 60 -- 48 hours

yay.create_autocmd("UpgradeSelect", {
  desc = "exclude AUR packages modified less than 48h ago",
  callback = function(event)
    local exclude = {}
    local now = os.time()

    for _, pkg in ipairs(event.data.upgrades) do
      if pkg.repository == "aur" and pkg.last_modified then
        local age = now - pkg.last_modified
        if age < cooldown then
          local hours = math.floor(age / 3600)
          yay.log.warn(pkg.name .. ": updated only " .. hours .. "h ago — skipping for now")
          table.insert(exclude, pkg.name)
        end
      end
    end

    if #exclude > 0 then
      return { exclude = exclude, skip_menu = false }
    end
  end,
})
