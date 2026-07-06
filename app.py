from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
from config.settings import use_mongodb, mongodb_uri, mongodb_database
app = Flask(__name__)
CORS(app)
# ── MongoDB lazy init ──────────────────────────────────────────────────────────
_mongo_db = None
def get_mongo_db():
    global _mongo_db
    if _mongo_db is None and use_mongodb:
        try:
            from modules.db import get_db
            _mongo_db = get_db(mongodb_uri, mongodb_database)
        except Exception as e:
            print(f"MongoDB init failed in app.py: {e}")
    return _mongo_db
_VALID_PAGE_SIZES = {10, 20, 50, 100}
def _parse_pagination():
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = int(request.args.get('page_size', 20))
        if page_size not in _VALID_PAGE_SIZES:
            page_size = 20
    except (ValueError, TypeError):
        page_size = 20
    return page, page_size
def _paginated_response(db, query, page, page_size):
    from modules.db import get_jobs_paginated
    result = get_jobs_paginated(db, query=query, sort_field="last_seen", sort_dir=-1,
                                page=page, page_size=page_size)
    return jsonify({
        "data":      [_map_job_doc(d) for d in result["docs"]],
        "total":     result["total"],
        "page":      result["page"],
        "page_size": result["page_size"],
        "pages":     result["pages"],
    })
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')
def _map_job_doc(doc):
    return {
        'Job_ID':                 doc.get('job_id', ''),
        'Title':                  doc.get('title', ''),
        'Company':                doc.get('company', ''),
        'Company_ID':             doc.get('company_id', 'Unknown'),
        'Company_Website':        doc.get('company_website', 'Unknown'),
        'Job_Category':           doc.get('job_category', 'Unknown'),
        'HR_Name':                doc.get('hr_name', 'Unknown'),
        'HR_Link':                doc.get('hr_link', 'Unknown'),
        'Job_Link':               doc.get('job_link', ''),
        'External_Job_link':      doc.get('external_job_link', ''),
        'Number_of_Applications': doc.get('num_applications', 'Unknown'),
        'Re_posted':              doc.get('reposted', False),
        'Is_Easy_Apply':          doc.get('is_easy_apply', False),
        'Date_Applied':           str(doc.get('date_applied', '')),
        'Date_Posted':            str(doc.get('date_posted', '')),
        'Status':                 doc.get('status', ''),
        'Work_Location':          doc.get('work_location', ''),
        'Work_Style':             doc.get('work_style', ''),
        'About_Job':              doc.get('about_job', ''),
        'Experience_Required':    doc.get('experience_required', ''),
        'Skills_Required':        doc.get('skills_required', ''),
        'Failure_Reason':         doc.get('failure_reason', ''),
        'Skip_Reason':            doc.get('skip_reason', ''),
        'Screenshot':             doc.get('screenshot', ''),
        'Visits_Count':           doc.get('visits_count', 1),
        'Last_Seen':              str(doc.get('last_seen', '')),
        'Posted_City':            doc.get('posted_city', 'Unknown'),
        'Posted_Duration':        doc.get('posted_duration', 'Unknown'),
        'People_Applied':         doc.get('people_applied'),   # int or None
    }
@app.route('/active-jobs', methods=['GET'])
def get_active_jobs():
    """Paginated active/captured jobs. Supports: page, page_size, is_easy_apply, status,
    hide_reposted, search, posted_city, posted_duration_type, min_people_applied."""
    try:
        db = get_mongo_db()
        if db is None:
            return jsonify({"error": "MongoDB not available"}), 503
        page, page_size = _parse_pagination()
        query = {"status": {"$in": ["Active", "New", "", None]}}
        is_easy = request.args.get('is_easy_apply')
        if is_easy == 'true':
            query['is_easy_apply'] = True
        elif is_easy == 'false':
            query['is_easy_apply'] = False
        if request.args.get('hide_reposted') == 'true':
            query['reposted'] = {"$ne": True}
        status_filter = request.args.get('status', '').strip()
        if status_filter in ('Active', 'New'):
            query['status'] = status_filter
        search = request.args.get('search', '').strip()
        if search:
            query['$or'] = [
                {'title':   {'$regex': search, '$options': 'i'}},
                {'company': {'$regex': search, '$options': 'i'}},
            ]
        # --- posted_city filter ---
        city_filter = request.args.get('posted_city', '').strip()
        if city_filter:
            query['posted_city'] = {'$regex': city_filter, '$options': 'i'}
        # --- posted_duration filter (hours / days / weeks / months) ---
        duration_type = request.args.get('posted_duration_type', '').strip()
        _dur_map = {'hours': 'hour', 'days': 'day', 'weeks': 'week', 'months': 'month'}
        if duration_type in _dur_map:
            query['posted_duration'] = {'$regex': _dur_map[duration_type], '$options': 'i'}
        # --- people_applied minimum filter ---
        min_people = request.args.get('min_people_applied', '').strip()
        if min_people:
            try:
                query['people_applied'] = {'$gte': int(min_people)}
            except ValueError:
                pass
        return _paginated_response(db, query, page, page_size)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/active-jobs/summary', methods=['GET'])
def get_active_jobs_summary():
    """Returns per-company job counts for active jobs, sorted by count descending."""
    try:
        db = get_mongo_db()
        if db is None:
            return jsonify({"error": "MongoDB not available"}), 503
        query = {"status": {"$in": ["Active", "New", "", None]}}
        from modules.db import get_company_job_counts
        data = get_company_job_counts(db, query)
        total = sum(d['count'] for d in data)
        return jsonify({"data": data, "total": total})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/active-jobs/<job_id>', methods=['PUT'])
def update_active_date(job_id):
    """Updates the date_applied field for a job."""
    try:
        new_date = datetime.now()
        db = get_mongo_db()
        if db is None:
            return jsonify({"error": "MongoDB not available"}), 503
        from modules.db import update_job_date
        updated = update_job_date(db, job_id, new_date)
        if updated:
            return jsonify({"message": "Date Applied updated successfully"}), 200
        return jsonify({"error": f"Job ID {job_id} not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/jobs/<job_id>', methods=['DELETE'])
def delete_job_endpoint(job_id):
    """Delete a job by job_id from the linkedin-jobs collection."""
    try:
        db = get_mongo_db()
        if db is None:
            return jsonify({"error": "MongoDB not available"}), 503
        from modules.db import delete_job
        deleted = delete_job(db, job_id)
        if deleted:
            return jsonify({"message": "Job deleted successfully"}), 200
        return jsonify({"error": f"Job ID {job_id} not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/failed-jobs', methods=['GET'])
def get_failed_jobs():
    """Paginated failed jobs. Supports: page, page_size, search."""
    try:
        db = get_mongo_db()
        if db is None:
            return jsonify({"error": "MongoDB not available"}), 503
        page, page_size = _parse_pagination()
        query = {"status": "Failed"}
        search = request.args.get('search', '').strip()
        if search:
            query['$or'] = [
                {'title':          {'$regex': search, '$options': 'i'}},
                {'company':        {'$regex': search, '$options': 'i'}},
                {'failure_reason': {'$regex': search, '$options': 'i'}},
            ]
        return _paginated_response(db, query, page, page_size)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/skipped-jobs', methods=['GET'])
def get_skipped_jobs():
    """Paginated skipped jobs. Supports: page, page_size, search."""
    try:
        db = get_mongo_db()
        if db is None:
            return jsonify({"error": "MongoDB not available"}), 503
        page, page_size = _parse_pagination()
        query = {"status": "Skipped"}
        search = request.args.get('search', '').strip()
        if search:
            query['$or'] = [
                {'title':       {'$regex': search, '$options': 'i'}},
                {'company':     {'$regex': search, '$options': 'i'}},
                {'skip_reason': {'$regex': search, '$options': 'i'}},
            ]
        return _paginated_response(db, query, page, page_size)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True)
