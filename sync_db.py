import threading, time, requests
#1v8C7zvn9zUpJgvYPOhMk6CxNvWsSDNFD
def update_db_periodically():
    while True:
        try:
            url = "https://drive.google.com/uc?id=1v8C7zvn9zUpJgvYPOhMk6CxNvWsSDNFD"
            r = requests.get(url)
            with open("db/pcs.db", "wb") as f:
                f.write(r.content)
            print("Database updated.")
        except Exception as e:
            print("Update failed:", e)
        time.sleep(3600)  # every hour

threading.Thread(target=update_db_periodically, daemon=True).start()
