// Settings live in the database, so the limits are re-applied from the environment on every start.
onBootstrap((e) => {
  e.next()
  const lib = require(`${__hooks}/ratelimit_lib.js`)
  const settings = e.app.settings()
  settings.rateLimits.enabled = ($os.getenv("PB_RATE_LIMITS_ENABLED") || "true").toLowerCase() !== "false"
  settings.rateLimits.rules = lib.parseRules($os.getenv("PB_RATE_LIMIT_RULES") || lib.DEFAULT_RULES)
  // Behind the reverse proxy every request arrives from the proxy's address, so the client IP comes from its header.
  settings.trustedProxy.headers = ($os.getenv("PB_TRUSTED_PROXY_HEADERS") || "X-Forwarded-For")
    .split(",")
    .map((header) => header.trim())
    .filter(Boolean)
  settings.trustedProxy.useLeftmostIP = false
  e.app.save(settings)
})
