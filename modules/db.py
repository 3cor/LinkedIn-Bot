"""
MongoDB helper module for LinkedIn Job Bot.

Single collection: linkedin-jobs
  - All job records (applied, failed, skipped) stored in one place.
  - `status`        — "Applied" | "Failed" | "Skipped" |
                      "Not Applied - External Link Captured" |
                      "Not Applied - No Apply Link Found"
  - `is_easy_apply` — True for Easy Apply, False for External Apply
  - `reposted`      — True when LinkedIn shows the job as reposted
  - `external_job_link` — always captured from the apply <a> href

Unique key: job_id
"""

from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError, OperationFailure
from datetime import datetime

COLLECTION = "linkedin-jobs"

_client = None
_db = None


# ── Connection ─────────────────────────────────────────────────────────────────

def get_db(uri: str, db_name: str):
    """
    Initialize (once) and return the MongoDB database instance.
    Raises ConnectionFailure if the server is unreachable.
    """
    global _client, _db
    if _db is None:
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        _client.admin.command('ping')
        _db = _client[db_name]
        print(f"✓ MongoDB connected: {uri}  /  database: {db_name}")
        print("  Verifying collection...")
        _ensure_collections(_db)
        _ensure_indexes(_db)
        print("  Collection and indexes are ready.")
    return _db


def _ensure_collections(db) -> None:
    """Ensure linkedin-jobs collection exists."""
    existing = db.list_collection_names()
    if COLLECTION not in existing:
        db[COLLECTION].insert_one({"_sentinel": True})
        db[COLLECTION].delete_one({"_sentinel": True})
        print(f"  ✓ Created MongoDB collection: {COLLECTION}")
    else:
        print(f"  ✓ Collection exists: {COLLECTION}")


def _create_unique_index(collection, field: str) -> None:
    """Create a unique index on `field`. Drops conflicting non-unique index first."""
    index_name = f"{field}_1"
    try:
        collection.create_index([(field, ASCENDING)], unique=True)
    except OperationFailure as e:
        if e.code == 86:
            print(f"  ⚠️  Conflicting index '{index_name}' — dropping and recreating as unique…")
            try:
                collection.drop_index(index_name)
                collection.create_index([(field, ASCENDING)], unique=True)
                print(f"  ✓ Re-created unique index '{index_name}'")
            except PyMongoError as drop_err:
                print(f"  ✗ Could not fix index: {drop_err}")
        else:
            raise


def _ensure_indexes(db) -> None:
    """Create required indexes on first connection."""
    col = db[COLLECTION]
    _create_unique_index(col, "job_id")
    col.create_index([("status", ASCENDING)])
    col.create_index([("date_applied", ASCENDING)])
    col.create_index([("reposted", ASCENDING)])
    col.create_index([("is_easy_apply", ASCENDING)])
    col.create_index([("visits_count", ASCENDING)])
    col.create_index([("last_seen", ASCENDING)])


def close_db() -> None:
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        print("MongoDB connection closed.")


# ── Job-ID loading (deduplication) ────────────────────────────────────────────

def check_and_touch_job(db, job_id: str, partial_doc: dict = None) -> bool:
    """
    Check whether job_id already exists in linkedin-jobs.
    If found:
      - Updates `last_seen` timestamp.
      - Increments `visits_count` by 1.
      - Upserts any fields supplied in `partial_doc` so the record stays current.

    Returns True if found, False if not seen before.
    """
    set_fields = {"last_seen": datetime.now()}
    if partial_doc:
        safe = {k: v for k, v in partial_doc.items()
                if k != "job_id"
                and v not in (None, "", "Unknown")
                and not (k == "external_job_link" and not str(v).startswith('http'))}
        set_fields.update(safe)

    try:
        result = db[COLLECTION].find_one_and_update(
            {"job_id": job_id},
            {
                "$set": set_fields,
                "$inc": {"visits_count": 1},
            },
            projection={"_id": 1}
        )
        return result is not None
    except PyMongoError as e:
        print(f"⚠️ MongoDB: check_and_touch_job failed for '{job_id}': {e}")
        return False


def get_all_job_ids(db) -> set:
    """Return a set of all known Job IDs from linkedin-jobs."""
    job_ids: set = set()
    try:
        ids = db[COLLECTION].distinct("job_id")
        job_ids.update(ids)
        print(f"  ✓ {COLLECTION}: {len(ids)} job IDs loaded")
    except PyMongoError as e:
        print(f"⚠️ MongoDB: Could not read job IDs from '{COLLECTION}': {e}")
    print(f"Loaded {len(job_ids)} previously seen Job IDs from MongoDB.")
    return job_ids


# ── Job upsert ─────────────────────────────────────────────────────────────────

def upsert_job(db, doc: dict) -> None:
    """
    Insert or update a job document in linkedin-jobs (with existence check).

    - Checks if job already exists (by job_id) before writing.
    - On insert:  sets `created_at` via $setOnInsert.
    - On update:  refreshes `last_seen`, increments `visits_count`.
    - URL guard:  `external_job_link` is only stored when it is a real http URL
                  so label strings never corrupt a previously stored valid URL.
    """
    try:
        set_doc = {k: v for k, v in doc.items()
                   if k != "visits_count"
                   and not (k == "external_job_link" and not str(v or '').startswith('http'))}
        set_doc["last_seen"] = datetime.now()

        db[COLLECTION].update_one(
            {"job_id": doc["job_id"]},
            {
                "$set": set_doc,
                "$inc": {"visits_count": 1},
                "$setOnInsert": {"created_at": datetime.now()},
            },
            upsert=True
        )
    except PyMongoError as e:
        print(f"⚠️ MongoDB: Failed to upsert job '{doc.get('job_id')}': {e}")


# ── Field updates ──────────────────────────────────────────────────────────────

def update_is_easy_apply(db, job_id: str, is_easy_apply: bool) -> bool:
    """
    Update ONLY the is_easy_apply field for a job in linkedin_jobs.
    Called when a job is re-detected (already-seen) to keep the flag accurate.
    Returns True if a document was matched.
    """
    try:
        result = db[COLLECTION].update_one(
            {"job_id": job_id},
            {"$set": {"is_easy_apply": is_easy_apply, "last_seen": datetime.now()}}
        )
        return result.matched_count > 0
    except PyMongoError as e:
        print(f"⚠️ MongoDB: update_is_easy_apply failed for '{job_id}': {e}")
        return False


def update_external_job_link(db, job_id: str, url: str) -> bool:
    """
    Update ONLY the external_job_link field for a job.
    Pure $set — does NOT touch visits_count.
    Returns True if a document was updated or already had this value.
    """
    if not url or not str(url).startswith('http'):
        return False
    try:
        result = db[COLLECTION].update_one(
            {"job_id": job_id},
            {"$set": {"external_job_link": url}}
        )
        return result.modified_count > 0 or result.matched_count > 0
    except PyMongoError as e:
        print(f"⚠️ MongoDB: update_external_job_link failed for '{job_id}': {e}")
        return False


# ── Query helpers ──────────────────────────────────────────────────────────────

def get_jobs(db, query: dict = None, sort_field: str = "last_seen",
             sort_dir: int = -1) -> list:
    """
    Retrieve job documents from linkedin-jobs.
    Pass a query dict to filter by status, is_easy_apply, reposted, etc.
    Returns documents newest-first by default (sort on last_seen).
    Excludes MongoDB internal _id.
    """
    try:
        cursor = db[COLLECTION].find(
            query or {},
            {"_id": 0}
        ).sort(sort_field, sort_dir)
        return list(cursor)
    except PyMongoError as e:
        print(f"⚠️ MongoDB: Failed to query {COLLECTION}: {e}")
        return []


def get_jobs_paginated(db, query: dict = None, sort_field: str = "last_seen",
                       sort_dir: int = -1, page: int = 1, page_size: int = 20) -> dict:
    """
    Paginated retrieval from linkedin-jobs.
    Returns { docs, total, page, page_size, pages }.
    """
    try:
        col = db[COLLECTION]
        q = query or {}
        total = col.count_documents(q)
        skip = (page - 1) * page_size
        cursor = col.find(q, {"_id": 0}).sort(sort_field, sort_dir).skip(skip).limit(page_size)
        docs = list(cursor)
        pages = max(1, (total + page_size - 1) // page_size)
        return {"docs": docs, "total": total, "page": page, "page_size": page_size, "pages": pages}
    except PyMongoError as e:
        print(f"⚠️ MongoDB: Failed to paginate {COLLECTION}: {e}")
        return {"docs": [], "total": 0, "page": page, "page_size": page_size, "pages": 1}


def update_job_date(db, job_id: str, new_date: datetime) -> bool:
    """Update the date_applied field for a single job."""
    try:
        result = db[COLLECTION].update_one(
            {"job_id": job_id},
            {"$set": {"date_applied": str(new_date), "updated_at": datetime.now()}}
        )
        return result.modified_count > 0
    except PyMongoError as e:
        print(f"⚠️ MongoDB: Failed to update date_applied for '{job_id}': {e}")
        return False


def get_company_job_counts(db, query: dict = None) -> list:
    """
    Return per-company job counts for jobs matching `query`, sorted by count descending.
    Each element: { "company": str, "count": int }
    """
    try:
        pipeline = [
            {"$match": query or {}},
            {"$group": {"_id": "$company", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$project": {"_id": 0, "company": "$_id", "count": 1}},
        ]
        return list(db[COLLECTION].aggregate(pipeline))
    except PyMongoError as e:
        print(f"⚠️ MongoDB: Failed to aggregate company counts: {e}")
        return []

