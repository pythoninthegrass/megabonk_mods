onRecordCreateRequest((e) => {
  const lib = require(`${__hooks}/level_lib.js`)
  lib.applyUploadedLevel(e)

  let code
  do {
    code = lib.newCode()
  } while (e.app.countRecords("levels", $dbx.hashExp({ code })) > 0)
  e.record.set("code", code)
  e.record.set("author", e.auth.id)
  e.record.set("downloads", 0)
  e.record.set("likes", 0)
  e.record.set("hidden", false)
  e.next()
}, "levels")

onRecordUpdateRequest((e) => {
  require(`${__hooks}/level_lib.js`).applyUploadedLevel(e)
  e.next()
}, "levels")

// The visibility lists are moderation data, shown only to site owners.
onRecordEnrich((e) => {
  const info = e.requestInfo
  if (!info || !(info.hasSuperuserAuth() || (info.auth && info.auth.getBool("admin")))) {
    e.record.hide("viewers", "blocked")
  }
  e.next()
}, "levels")

// Names a downloaded level file after its title.
onFileDownloadRequest((e) => {
  if (e.fileField.name === "level" && e.requestInfo().query["download"]) {
    const lib = require(`${__hooks}/level_lib.js`)
    const filename = `${lib.slugify(e.record.getString("title"))}.mblevel.json`
    e.requestEvent.response.header().set("Content-Disposition", `attachment; filename="${filename}"`)
  }
  e.next()
}, "levels")

routerAdd("GET", "/api/l/{code}/download", (e) => {
  const code = e.request.pathValue("code").toUpperCase()
  let level
  try {
    level = $app.findFirstRecordByFilter("levels", "code = {:code}", { code })
  } catch (_) {
    throw new NotFoundError("Level not found.")
  }
  if (!$app.canAccessRecord(level, e.requestInfo(), $app.findCollectionByNameOrId("levels").viewRule)) {
    throw new NotFoundError("Level not found.")
  }
  $app.db().newQuery("UPDATE levels SET downloads = downloads + 1 WHERE id = {:id}").bind({ id: level.id }).execute()
  return e.redirect(302, `/api/files/levels/${level.id}/${level.getString("level")}?download=1`)
})
