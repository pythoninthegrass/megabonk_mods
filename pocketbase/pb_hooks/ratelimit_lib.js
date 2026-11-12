// One rule per comma: "<label> <max requests> <seconds>"; the label may contain spaces, such as "POST /api/collections/".
const DEFAULT_RULES = "*:auth 2 3, *:create 20 5, /api/batch 3 1, /api/ 300 10, /api/l/ 30 60, levels:create 10 60"

function parseRules(text) {
  return text
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const tokens = part.split(/\s+/)
      const duration = parseInt(tokens.pop(), 10)
      const maxRequests = parseInt(tokens.pop(), 10)
      const label = tokens.join(" ")
      if (!label || !(maxRequests > 0) || !(duration > 0)) {
        throw new Error(`invalid PB_RATE_LIMIT_RULES entry: "${part}"`)
      }
      return { label, audience: "", maxRequests, duration }
    })
}

module.exports = { DEFAULT_RULES, parseRules }
