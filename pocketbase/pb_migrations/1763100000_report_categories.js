/// <reference path="../pb_data/types.d.ts" />

const NO_SERVER_FIELDS = "@request.body.status:isset = false && @request.body.missing:isset = false && @request.body.notifiedAt:isset = false"
const CATEGORIES = ["copyright", "broken", "inappropriate", "other"]
const STATUSES = ["new", "incomplete", "needs-info", "valid", "rejected"]
const ADDED_FIELDS = [
  "pack", "category", "status", "missing", "notifiedAt", "contactEmail", "contactAddress", "contactPhone",
  "work", "itemUrl", "goodFaith", "accurate", "fairUseConsidered", "signature",
]

migrate(
  (app) => {
    const reports = app.findCollectionByNameOrId("reports")
    const packs = app.findCollectionByNameOrId("packs")
    reports.fields.getByName("level").required = false
    reports.fields.getByName("reason").required = false
    reports.fields.add(
      new RelationField({ name: "pack", collectionId: packs.id, maxSelect: 1, cascadeDelete: true }),
      new SelectField({ name: "category", maxSelect: 1, values: CATEGORIES }),
      new SelectField({ name: "status", maxSelect: 1, values: STATUSES }),
      new JSONField({ name: "missing", maxSize: 2000 }),
      new DateField({ name: "notifiedAt" }),
      new TextField({ name: "contactEmail", max: 320 }),
      new TextField({ name: "contactAddress", max: 500 }),
      new TextField({ name: "contactPhone", max: 50 }),
      new TextField({ name: "work", max: 2000 }),
      new TextField({ name: "itemUrl", max: 500 }),
      new BoolField({ name: "goodFaith" }),
      new BoolField({ name: "accurate" }),
      new BoolField({ name: "fairUseConsidered" }),
      new TextField({ name: "signature", max: 200 }),
    )
    reports.createRule = `@request.auth.id != '' && @request.body.user = @request.auth.id && ${NO_SERVER_FIELDS}`
    app.save(reports)
  },
  (app) => {
    const reports = app.findCollectionByNameOrId("reports")
    for (const name of ADDED_FIELDS) reports.fields.removeByName(name)
    reports.fields.getByName("level").required = true
    reports.fields.getByName("reason").required = true
    reports.createRule = "@request.auth.id != '' && @request.body.user = @request.auth.id"
    app.save(reports)
  },
)
