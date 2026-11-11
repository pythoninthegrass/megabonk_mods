const MAX_TITLE_LENGTH = 200
const CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
const SLOPES = ["north", "south", "east", "west"]
const TILE_OPS = ["tile.setHeight", "tile.setSlope", "tile.add", "tile.remove"]

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value)
const isVector3 = (value) => Array.isArray(value) && value.length === 3 && value.every((n) => typeof n === "number" && isFinite(n))

function checkGrid(level, errors) {
  const scratch = level.baseline === "none"
  if (!scratch) {
    if (level.grid !== undefined) errors.push("grid is only allowed on a from-scratch level (baseline \"none\")")
    return
  }
  const grid = level.grid
  if (!isObject(grid)) return errors.push("grid is required on a from-scratch level")
  if (!Number.isInteger(grid.width) || grid.width < 1 || !Number.isInteger(grid.depth) || grid.depth < 1) {
    return errors.push("grid width and depth must be integers of at least 1")
  }
  if (!Array.isArray(grid.cells)) return errors.push("grid cells must be a list")
  const seen = {}
  for (const cell of grid.cells) {
    if (!isObject(cell) || !Number.isInteger(cell.x) || !Number.isInteger(cell.z) || typeof cell.height !== "number") {
      return errors.push("grid cells need integer x and z and a numeric height")
    }
    if (cell.x < 0 || cell.x >= grid.width || cell.z < 0 || cell.z >= grid.depth) {
      return errors.push(`grid cell (${cell.x}, ${cell.z}) lies outside the ${grid.width} by ${grid.depth} grid`)
    }
    if (cell.slope !== undefined && SLOPES.indexOf(cell.slope) < 0) {
      return errors.push(`grid cell (${cell.x}, ${cell.z}) has an unknown slope`)
    }
    const key = `${cell.x},${cell.z}`
    if (seen[key]) return errors.push(`grid cell (${cell.x}, ${cell.z}) appears more than once`)
    seen[key] = true
  }
  for (const name of ["spawn", "bossSpawner"]) {
    if (!isObject(level[name]) || !isVector3(level[name].position)) {
      errors.push(`grid: ${name} with a three-number position is required on a from-scratch level`)
    }
  }
}

function checkEdits(level, errors) {
  if (level.edits === undefined) return
  if (!Array.isArray(level.edits)) return errors.push("edits must be a list")
  const scratch = level.baseline === "none"
  for (const [index, edit] of level.edits.entries()) {
    if (!isObject(edit) || typeof edit.opType !== "string" || edit.opType === "") {
      return errors.push(`edits[${index}] must be an object with an opType`)
    }
    for (const field of ["target", "payload"]) {
      if (edit[field] !== undefined && typeof edit[field] !== "string") {
        return errors.push(`edits[${index}].${field} must be a string`)
      }
    }
    if (scratch && (TILE_OPS.indexOf(edit.opType) >= 0 || (edit.target || "").indexOf("gen:") === 0)) {
      return errors.push(`edits[${index}] edits generated terrain, which a from-scratch level does not have`)
    }
  }
}

function checkPacks(level, errors) {
  if (level.packs === undefined) return
  const valid = isObject(level.packs) && Object.keys(level.packs).every((id) => typeof level.packs[id] === "string")
  if (!valid) errors.push("packs must map pack ids to version strings")
}

// Returns {errors} or {level, metadata}; metadata holds the record fields derived from the file.
function parseLevel(text) {
  let level
  try {
    level = JSON.parse(text)
  } catch (_) {
    return { errors: ["The level file is not valid JSON"] }
  }
  if (!isObject(level)) return { errors: ["The level file must be a JSON object"] }

  const errors = []
  if (!Number.isInteger(level.schemaVersion) || level.schemaVersion < 1 || level.schemaVersion > 4) {
    errors.push("schemaVersion must be an integer from 1 to 4")
  }
  if (typeof level.title !== "string" || level.title.trim() === "") {
    errors.push("title is required, since a level without one is not listed on Map Selection")
  } else if (level.title.trim().length > MAX_TITLE_LENGTH) {
    errors.push(`title must be at most ${MAX_TITLE_LENGTH} characters`)
  }
  if (level.map !== undefined && !Number.isInteger(level.map)) errors.push("map must be an integer")
  if (level.gameBuildId !== undefined && typeof level.gameBuildId !== "string") errors.push("gameBuildId must be a string")
  if (level.baseline !== undefined && level.baseline !== "generated" && level.baseline !== "none") {
    errors.push("baseline must be \"generated\" or \"none\"")
  }
  checkPacks(level, errors)
  checkGrid(level, errors)
  checkEdits(level, errors)
  if (errors.length) return { errors }

  return {
    level,
    metadata: {
      title: level.title.trim(),
      packs: level.packs || {},
      schemaVersion: level.schemaVersion,
      gameBuildId: level.gameBuildId || "",
      map: level.map || 0,
    },
  }
}

function slugify(title) {
  const slug = title
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
  return slug || "level"
}

function newCode() {
  const raw = $security.randomStringWithAlphabet(9, CODE_ALPHABET)
  return `${raw.slice(0, 3)}-${raw.slice(3, 6)}-${raw.slice(6)}`
}

// Reads the uploaded level file, rejects an invalid one and copies the derived fields onto the record.
function applyUploadedLevel(e) {
  if (String(e.requestInfo().headers["content_type"] || "").indexOf("multipart/form-data") !== 0) return
  // findUploadedFiles throws, rather than returning an empty list, when the request has no such file.
  let uploads
  try {
    uploads = e.findUploadedFiles("level")
  } catch (_) {
    return
  }
  if (uploads.length === 0) return
  const reader = uploads[0].reader.open()
  let text
  try {
    text = toString(reader)
  } finally {
    reader.close()
  }
  const parsed = parseLevel(text)
  if (parsed.errors) {
    const message = parsed.errors.join("; ")
    throw new BadRequestError(`Invalid level file: ${message}`, {
      level: { code: "validation_invalid_level_file", message },
    })
  }
  for (const [field, value] of Object.entries(parsed.metadata)) {
    e.record.set(field, value)
  }
}

module.exports = { applyUploadedLevel, slugify, newCode }
