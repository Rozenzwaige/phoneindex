from flask import Flask, request, render_template
from google.cloud import bigquery
import os

# 🔍 בדיקות לוגים על משתנה הסביבה והקובץ
secrets_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/etc/secrets/telephones-449210-ea0631866678.json")
print(f"🔍 GOOGLE_APPLICATION_CREDENTIALS מוגדר כ: {secrets_path}")

# בדיקה אם הקובץ קיים
if os.path.exists(secrets_path):
    print(f"✅ נמצא קובץ credentials בנתיב: {secrets_path}")
    try:
        with open(secrets_path, 'r') as file:
            print("✅ הצלחנו לקרוא את קובץ ההרשאות!")
    except Exception as e:
        print(f"❌ שגיאה בגישה לקובץ: {e}")
else:
    print(f"❌ הקובץ {secrets_path} לא נמצא! בדוק את הנתיב והאם הוא קיים.")

# יצירת מופע Flask
app = Flask(__name__, template_folder="templates")

# קביעת GOOGLE_APPLICATION_CREDENTIALS שוב (ליתר ביטחון)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = secrets_path

# יצירת חיבור ל-BigQuery עם בדיקה
try:
    client = bigquery.Client()
    print("✅ החיבור ל-BigQuery הצליח!")
except Exception as e:
    print(f"❌ שגיאה בחיבור ל-BigQuery: {e}")
    client = None  # נוודא שהאפליקציה לא תקרוס

# דף הבית - טופס חיפוש
@app.route('/')
def home():
    return render_template('index.html')

# נתיב לביצוע חיפוש
@app.route('/search', methods=['GET'])
def search():
    if client is None:
        return "❌ שגיאה: אין חיבור ל-BigQuery", 500  # החזר שגיאה אם אין חיבור

    query = request.args.get('query', '').strip()
    search_type = request.args.get('search_type', 'free')

    if not query:
        return render_template('results.html', results=[], query=query, search_type=search_type)

    words = query.split()  # פיצול המילים לחיפוש

    # יצירת תנאי SQL מותאם לכל סוג חיפוש
    if search_type == "name":
        conditions = " AND ".join([f"name LIKE '%{word}%'" for word in words])
    elif search_type == "title":
        conditions = " AND ".join([f"title LIKE '%{word}%'" for word in words])
    else:  # חיפוש חופשי בכל העמודות
        conditions = " AND ".join([f"(name LIKE '%{word}%' OR title LIKE '%{word}%')" for word in words])

    sql = f"SELECT name, title, phone FROM telephones-449210.ALLPHONES.phones_fixed WHERE {conditions}"

    try:
        results = client.query(sql).result()
        data = [row for row in results]
        print(f"✅ נמצאו {len(data)} תוצאות.")
    except Exception as e:
        print(f"❌ שגיאה בביצוע השאילתה: {e}")
        return "❌ שגיאה בחיפוש נתונים", 500

    return render_template('results.html', results=data, query=query, search_type=search_type)

# 🔍 נתיב Health Check כדי לוודא שהאפליקציה פועלת
@app.route('/health', methods=['GET'])
def health_check():
    if client is None:
        return {"status": "error", "message": "❌ חיבור ל-BigQuery נכשל"}, 500
    return {"status": "ok", "message": "✅ האפליקציה רצה בהצלחה"}, 200

# הפעלת השרת
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
