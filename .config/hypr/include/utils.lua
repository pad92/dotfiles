local M = {}

-- Helper to launch apps via UWSM
function M.uwsm_app(cmd)
  hl.exec_cmd("uwsm app -- " .. cmd)
end

-- Utility helper to enforce floating behavior on multiple window classes
function M.set_float(classes)
  if type(classes) == "string" then classes = { classes } end
  for _, class in ipairs(classes) do
    hl.window_rule({ match = { class = "^(" .. class .. ")$" }, float = true })
  end
end

return M
