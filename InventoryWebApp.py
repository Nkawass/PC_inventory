from flask import Flask, render_template, request, Response
import sqlite3, os, csv, io
import threading, time, requests
import math

app = Flask(__name__)
DB_PATH = 'db/pcs.db'

def get_filtered_data(filters, sort_by="timestamp", sort_order="desc"):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM pc_info WHERE 1=1"
    params = []

    for field in [
        "manufacturer", "model", "cpu", "ram", "gpu",
        "serial", "issues", "supplier"
    ]:
        value = filters.get(field)
        if value:
            query += f" AND {field} LIKE ?"
            params.append(f"%{value}%")

    # ✅ Date range filter for timestamp
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")

    if start_date:
        query += " AND DATE(timestamp) >= DATE(?)"
        params.append(start_date)
    if end_date:
        query += " AND DATE(timestamp) <= DATE(?)"
        params.append(end_date)

    allowed_sort_fields = [
        "manufacturer", "serial", "model", "cpu", "ram", "storage",
        "resolution", "camera", "touch", "issues", "gpu", "supplier", "timestamp"
    ]
    if sort_by not in allowed_sort_fields:
        sort_by = "timestamp"

    query += f" ORDER BY {sort_by} {sort_order.upper() if sort_order in ['asc', 'desc'] else 'DESC'}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


@app.route("/", methods=["GET"])
def index():
    filters = request.args
    sort_by = filters.get("sort_by", "timestamp")
    sort_order = filters.get("sort_order", "desc")
    page = int(filters.get("page", 1))
    per_page = 75

    all_pcs = get_filtered_data(filters, sort_by, sort_order)
    total_records = len(all_pcs)
    total_pages = math.ceil(total_records / per_page)

    # Slice for pagination
    start = (page - 1) * per_page
    end = start + per_page
    pcs = all_pcs[start:end]

    return render_template(
        "index.html",
        pcs=pcs,
        current_sort=sort_by,
        current_order=sort_order,
        current_page=page,
        total_pages=total_pages
    )

@app.route("/download-csv")
def download_csv():
    filters = request.args
    sort_by = filters.get("sort_by", "timestamp")
    sort_order = filters.get("sort_order", "desc")
    pcs = get_filtered_data(filters, sort_by, sort_order)

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    if pcs:
        writer.writerow(pcs[0].keys())  # headers
        for row in pcs:
            writer.writerow(row)

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=techdeal_inventory.csv"}
    )

# Background DB update
def update_db_periodically():
    while True:
        try:
            url = "https://drive.google.com/uc?id=1vWukuzL09RAWW1aWKdBTlqK8oG-4c51m"
            r = requests.get(url)
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
                print("🗑️ Old database deleted.")
            with open(DB_PATH, "wb") as f:
                f.write(r.content)
            print("✅ Database updated.")
        except Exception as e:
            print("Update failed:", e)
        time.sleep(3600)

threading.Thread(target=update_db_periodically, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True)
