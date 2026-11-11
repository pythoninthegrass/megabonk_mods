// Recomputes the stored count from the like records so it cannot drift.
function recountLikes(e) {
  $app
    .db()
    .newQuery("UPDATE levels SET likes = (SELECT COUNT(*) FROM likes WHERE level = {:id}) WHERE id = {:id}")
    .bind({ id: e.record.getString("level") })
    .execute()
  e.next()
}

onRecordAfterCreateSuccess(recountLikes, "likes")
onRecordAfterDeleteSuccess(recountLikes, "likes")
