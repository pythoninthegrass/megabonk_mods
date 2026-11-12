onRecordCreateRequest((e) => {
  require(`${__hooks}/pack_lib.js`).applyUploadedPack(e)
  e.record.set("downloads", 0)
  e.record.set("hidden", false)
  e.next()
}, "packs")

// The visibility lists are moderation data, shown only to site owners.
onRecordEnrich((e) => {
  const info = e.requestInfo
  if (!info || !(info.hasSuperuserAuth() || (info.auth && info.auth.getBool("admin")))) {
    e.record.hide("viewers", "blocked")
  }
  e.next()
}, "packs")

onRecordsListRequest((e) => {
  require(`${__hooks}/level_lib.js`).rejectVisibilityListProbes(e)
  e.next()
}, "packs")

onRecordViewRequest((e) => {
  require(`${__hooks}/level_lib.js`).rejectVisibilityListProbes(e)
  e.next()
}, "packs")

// Serves the pack as a zip that unpacks into UserData/LevelPacks/, laid out <id>/<id>, <id>/manifest.json, <id>/attachments.json.
routerAdd("GET", "/api/p/{id}/download", (e) => {
  const lib = require(`${__hooks}/pack_lib.js`)
  const packId = e.request.pathValue("id")
  const query = e.requestInfo().query
  if (!lib.PACK_ID.test(packId)) throw new NotFoundError("Pack not found.")
  const field = lib.PLATFORMS[query["platform"]]
  if (!field) throw new BadRequestError("platform must be windows or linux.")

  const viewRule = $app.findCollectionByNameOrId("packs").viewRule
  const visible = $app
    .findRecordsByFilter("packs", "packId = {:packId}", "-created", 0, 0, { packId })
    .filter((record) => $app.canAccessRecord(record, e.requestInfo(), viewRule))
  const pack = query["version"] ? visible.find((record) => record.getString("version") === query["version"]) : visible[0]
  if (!pack || !pack.getString(field)) throw new NotFoundError("Pack not found for that platform.")

  $app.db().newQuery("UPDATE packs SET downloads = downloads + 1 WHERE id = {:id}").bind({ id: pack.id }).execute()
  const workDir = `${$os.tempDir()}/pack-${$security.randomString(12)}`
  try {
    lib.serveZip(e, pack, field, workDir)
  } finally {
    $os.removeAll(workDir)
  }
})
