from flask import Flask, render_template, request, Response
import sqlite3, os, csv, io
import threading, time, requests
import math

app = Flask(__name__)
DB_PATH = 'db/pcs.db'
ALT_DB_PATH = 'db/inventory_shipped.db'

def get_filtered_data(filters, sort_by="timestamp", sort_order="desc"):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM pc_info WHERE 1=1"
    params = []

    for field in ["manufacturer", "model", "cpu", "gpu", "serial", "issues", "supplier", "touch", "resolution"]:
        if field == "cpu":
            cpu_values = filters.getlist("cpu")
            if cpu_values:
                query += f" AND cpu IN ({','.join('?' * len(cpu_values))})"
                params.extend(cpu_values)
        elif field == "model":
            value = filters.get(field)
            if value:  # ✅ Ensure value is not None or empty
                query += f" AND LOWER({field}) = ?"
                params.append(value.lower())

        else:
            value = filters.get(field)
            if value:
                if field == "resolution":
                    query += f" AND {field} = ?"
                    params.append(value)
                else:
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
        "resolution", "camera", "touch", "issues", "gpu", "supplier", "timestamp" , "QTY"
    ]
    if sort_by not in allowed_sort_fields:
        sort_by = "timestamp"

    query += f" ORDER BY {sort_by} {sort_order.upper() if sort_order in ['asc', 'desc'] else 'DESC'}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

# for the second database
def get_filtered_alt_data(filters, sort_by="Shipping_Time", sort_order="desc"):
        conn = sqlite3.connect(ALT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM shipped_inventory WHERE 1=1"
        params = []

        for field in ["Brand", "Model", "Supplier", "Touch", "IT Guy"]:
            value = filters.get(field)
            if value:
                query += f" AND [{field}] LIKE ?"
                params.append(f"%{value}%")

        cpu_values = filters.getlist("CPU")
        if cpu_values:
            query += f" AND CPU IN ({','.join('?' * len(cpu_values))})"
            params.extend(cpu_values)

        # Date filter on Shipping_Time
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        if start_date:
            query += " AND DATE([Shipping_Time]) >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND DATE([Shipping_Time]) <= DATE(?)"
            params.append(end_date)

        allowed_sort_fields = [
            "Brand", "TD Num", "Model", "Generation", "CPU", "RAM", "Resolution",
            "Touch", "Issues", "Supplier", "QTY", "Shipping_Time", "IT Guy"
        ]
        if sort_by not in allowed_sort_fields:
            sort_by = "Shipping_Time"

        query += f" ORDER BY [{sort_by}] {sort_order.upper() if sort_order in ['asc', 'desc'] else 'DESC'}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows


def get_unique_models():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT model FROM pc_info 
        WHERE model IS NOT NULL AND TRIM(model) != ''
        ORDER BY model
    """)
    models = [row[0] for row in cursor.fetchall()]
    conn.close()
    return models

def get_unique_cpus(model=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if model:
        cursor.execute("""
            SELECT DISTINCT cpu FROM pc_info 
            WHERE LOWER(model) = LOWER(?) AND cpu IS NOT NULL AND TRIM(cpu) != ''
            ORDER BY cpu
        """, (model,))
    else:
        cursor.execute("""
            SELECT DISTINCT cpu FROM pc_info 
            WHERE cpu IS NOT NULL AND TRIM(cpu) != ''
            ORDER BY cpu
        """)
    cpus = [row[0] for row in cursor.fetchall()]
    conn.close()
    return cpus

# for alt DB
def get_alt_cpu_options():
    conn = sqlite3.connect(ALT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT CPU FROM shipped_inventory WHERE CPU IS NOT NULL AND TRIM(CPU) != '' ORDER BY CPU")
    cpus = [row[0] for row in cursor.fetchall()]
    conn.close()
    return cpus


@app.route("/", methods=["GET"])
def index():
    filters = request.args
    sort_by = filters.get("sort_by", "timestamp")
    sort_order = filters.get("sort_order", "desc")
    page = int(filters.get("page", 1))
    per_page = 50

    selected_model = filters.get("model", "")
    cpu_options = get_unique_cpus(selected_model)  # depends on selected model

    all_pcs = get_filtered_data(filters, sort_by, sort_order)
    total_records = len(all_pcs)
    total_pages = math.ceil(total_records / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    pcs = all_pcs[start:end]

    model_options = get_unique_models()

    model = request.args.get("model", "").strip()
    resolution_options = []

    if model:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT resolution FROM pc_info WHERE LOWER(model) = LOWER(?) AND resolution IS NOT NULL",
            (model,))
        resolution_options = [row[0] for row in cursor.fetchall()]
        conn.close()

    return render_template("index.html", pcs=pcs, current_sort=sort_by, current_order=sort_order,
        current_page=page,
        total_pages=total_pages,
        cpu_options=cpu_options,
                           model_options=model_options,
                           resolution_options=resolution_options, total_records=total_records)



# to export csv in application
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


#rout for another webpage
@app.route("/alternate", methods=["GET"])
def alternate():
    filters = request.args
    sort_by = filters.get("sort_by", "Shipping_Time")
    sort_order = filters.get("sort_order", "desc")
    page = int(filters.get("page", 1))
    per_page = 50

    all_pcs = get_filtered_alt_data(filters, sort_by, sort_order)
    total_records = len(all_pcs)
    total_pages = math.ceil(total_records / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    pcs = all_pcs[start:end]

    cpu_options = get_alt_cpu_options()

    return render_template(
        "alternate.html",
        pcs=pcs,
        current_sort=sort_by,
        current_order=sort_order,
        current_page=page,
        total_pages=total_pages,
        cpu_options=cpu_options
    )



# Background DB update for both dbs
def update_db_periodically():
    while True:
        try:
            url1 = "https://drive.google.com/uc?id=1vWukuzL09RAWW1aWKdBTlqK8oG-4c51m"
            url2 = "https://drive.google.com/uc?id=1fPFZayOL0nAQAN6UB45Q5Nkxe7hlXlk9"  # Your second DB file
            for url, path in [(url1, DB_PATH), (url2, ALT_DB_PATH)]:
                r = requests.get(url)
                if os.path.exists(path):
                    os.remove(path)
                    print(f"🗑️ Old database deleted: {path}")
                with open(path, "wb") as f:
                    f.write(r.content)
                print(f"✅ Database updated: {path}")
        except Exception as e:
            print("Update failed:", e)
        time.sleep(3600)


threading.Thread(target=update_db_periodically, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True)
