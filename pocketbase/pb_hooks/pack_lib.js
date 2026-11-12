const MAX_TOTAL_BYTES = 30 * 1024 * 1024
const PACK_ID = /^[a-z0-9][a-z0-9_-]{0,63}$/
const PLATFORMS = { windows: "bundleWindows", linux: "bundleLinux" }
const UPLOAD_FIELDS = ["manifest", "attachments", "bundleWindows", "bundleLinux"]

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value)

// Applies the PackManifest.Parse rules (docs/asset-bundles.md); returns {errors} or {manifest, metadata}.
function parseManifest(text, packId) {
  let manifest
  try {
    manifest = JSON.parse(text)
  } catch (_) {
    return { errors: ["manifest.json is not valid JSON"] }
  }
  if (!isObject(manifest)) return { errors: ["manifest.json must be a JSON object"] }

  const errors = []
  if (typeof manifest.id !== "string") errors.push("id must be a string")
  else if (manifest.id !== packId) errors.push(`id "${manifest.id}" must equal the pack id "${packId}"`)
  if (typeof manifest.version !== "string" || manifest.version.trim() === "") errors.push("version must be a non-empty string")
  if (!Array.isArray(manifest.assets) || !manifest.assets.every((asset) => typeof asset === "string")) {
    errors.push("assets must be a list of strings")
  }
  for (const name of ["name", "author"]) {
    if (manifest[name] !== undefined && typeof manifest[name] !== "string") errors.push(`${name} must be a string`)
  }
  if (errors.length) return { errors }

  return {
    manifest,
    metadata: {
      version: manifest.version.trim(),
      name: (manifest.name || "").trim(),
      assetCount: manifest.assets.length,
    },
  }
}

function parseAttachments(text) {
  try {
    if (isObject(JSON.parse(text))) return { errors: [] }
  } catch (_) {
    return { errors: ["attachments.json is not valid JSON"] }
  }
  return { errors: ["attachments.json must be a JSON object"] }
}

function totalSize(sizes) {
  return Object.values(sizes).reduce((sum, size) => sum + size, 0)
}

function formatMebibytes(bytes) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MiB`
}

// Returns {field: message} for everything wrong with an upload described by its text and sizes.
function validateUpload({ packId, manifestText, attachmentsText, sizes }) {
  const problems = {}
  if (typeof packId !== "string" || !PACK_ID.test(packId)) {
    problems.packId = "The pack id must be 1 to 64 characters of lowercase letters, digits, hyphens and underscores, starting with a letter or digit"
  }
  if (manifestText === null) {
    problems.manifest = "manifest.json is required"
  } else {
    const parsed = parseManifest(manifestText, packId)
    if (parsed.errors) problems.manifest = `Invalid manifest.json: ${parsed.errors.join("; ")}`
  }
  if (attachmentsText === null) {
    problems.attachments = "attachments.json is required"
  } else {
    const parsed = parseAttachments(attachmentsText)
    if (parsed.errors.length) problems.attachments = `Invalid attachments.json: ${parsed.errors.join("; ")}`
  }
  if (!sizes.bundleWindows && !sizes.bundleLinux) {
    problems.bundleWindows = "Upload a Windows bundle, a Linux bundle or both: at least one bundle is required"
  }
  const total = totalSize(sizes)
  if (total > MAX_TOTAL_BYTES) {
    problems.bundleWindows = problems.bundleWindows || `A pack can be at most 30 MiB in total; this upload is ${formatMebibytes(total)}`
  }
  return problems
}

function downloadFilename(packId, version, platform) {
  return `${packId}-${version.replace(/[^A-Za-z0-9._-]/g, "_")}-${platform}.zip`
}

// Returns the uploaded file for a field, or null when the request carries none (findUploadedFiles throws then).
function uploadedFile(e, field) {
  try {
    const files = e.findUploadedFiles(field)
    return files.length ? files[0] : null
  } catch (_) {
    return null
  }
}

function readText(file) {
  const reader = file.reader.open()
  try {
    return toString(reader)
  } finally {
    reader.close()
  }
}

const isSiteOwner = (e) => e.hasSuperuserAuth() || Boolean(e.auth && e.auth.getBool("admin"))

// Validates an upload, claims or checks the pack id, and copies the derived fields and sizes onto the record.
function applyUploadedPack(e) {
  const packId = e.record.getString("packId")
  const files = {}
  const sizes = {}
  for (const field of UPLOAD_FIELDS) {
    files[field] = uploadedFile(e, field)
    if (files[field]) sizes[field] = files[field].size
  }
  const problems = validateUpload({
    packId,
    manifestText: files.manifest ? readText(files.manifest) : null,
    attachmentsText: files.attachments ? readText(files.attachments) : null,
    sizes,
  })

  const existing = PACK_ID.test(packId) ? e.app.findRecordsByFilter("packs", "packId = {:packId}", "-created", 0, 0, { packId }) : []
  const owner = existing.length ? existing[0].getString("author") : e.auth.id
  if (owner !== e.auth.id && !isSiteOwner(e)) {
    problems.packId = `The pack id "${packId}" belongs to another player. Choose a different id.`
  }
  if (Object.keys(problems).length) {
    const data = {}
    for (const [field, message] of Object.entries(problems)) data[field] = new ValidationError("validation_invalid_pack_upload", message)
    throw new BadRequestError("Invalid pack upload.", data)
  }

  const metadata = parseManifest(readText(files.manifest), packId).metadata
  if (existing.some((record) => record.getString("version") === metadata.version)) {
    throw new BadRequestError("Invalid pack upload.", {
      manifest: new ValidationError("validation_duplicate_version", `Version ${metadata.version} of this pack is already uploaded. Raise the version in manifest.json.`),
    })
  }
  for (const [field, value] of Object.entries(metadata)) e.record.set(field, value)
  e.record.set("author", owner)
  e.record.set("sizeWindows", sizes.bundleWindows || 0)
  e.record.set("sizeLinux", sizes.bundleLinux || 0)
}

// Links the stored files under their installed names, zips the folder and serves the archive; the caller removes workDir.
function serveZip(e, pack, field, workDir) {
  const packId = pack.getString("packId")
  const dataDir = $app.dataDir()
  // A relative data directory would resolve against each link's own folder, so anchor it to the working directory.
  const root = dataDir.startsWith("/") ? dataDir : `${$os.getwd()}/${dataDir}`
  const stored = `${root}/storage/${pack.baseFilesPath()}`
  $os.mkdirAll(`${workDir}/${packId}`, 0o755)
  const installedNames = { [field]: packId, manifest: "manifest.json", attachments: "attachments.json" }
  for (const [source, name] of Object.entries(installedNames)) {
    $os.cmd("ln", "-s", `${stored}/${pack.getString(source)}`, `${workDir}/${packId}/${name}`).run()
  }
  // zip follows the links; -0 stores the already compressed bundle as is and -D leaves out directory entries.
  const zip = $os.cmd("zip", "-0", "-D", "-q", "-r", "pack.zip", packId)
  zip.dir = workDir
  zip.run()
  const platform = field === PLATFORMS.windows ? "windows" : "linux"
  e.response.header().set("Content-Disposition", `attachment; filename="${downloadFilename(packId, pack.getString("version"), platform)}"`)
  e.fileFS($os.dirFS(workDir), "pack.zip")
}

module.exports = {
  MAX_TOTAL_BYTES,
  PACK_ID,
  PLATFORMS,
  UPLOAD_FIELDS,
  parseManifest,
  parseAttachments,
  validateUpload,
  applyUploadedPack,
  serveZip,
  downloadFilename,
}
