from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)
DB_PATH = 'pc_info.db'  # Change if your DB is named differently

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

    # Validate sort_by to avoid SQL injection
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
    pcs = get_filtered_data(filters, sort_by, sort_order)
    return render_template("index.html", pcs=pcs, current_sort=sort_by, current_order=sort_order)




if __name__ == '__main__':
    app.run(debug=True)
