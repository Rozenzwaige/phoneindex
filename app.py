from flask import Flask, request, render_template, redirect, url_for, session
from flask_session import Session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from google_auth_oauthlib.flow import Flow
from google.cloud import bigquery
import google.auth.transport.requests
import google.oauth2.id_token
import json
import os

# יצירת אפליקציית Flask
app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecretkey"  # שנה למפתח חזק יותר

# הגדרות Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.route('/')
def home():
    return render_template('index.html', user=current_user)

# הגדרות Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# מחלקת משתמש
class User(UserMixin):
    def __init__(self, user_id, name, email):
        self.id = user_id
        self.name = name
        self.email = email

# מאגר משתמשים זמני (כדאי לשמור ב-DB אמיתי)
users = {}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

# הגדרת Google OAuth 2.0
GOOGLE_CLIENT_SECRET_FILE = "client_secret.json"

flow = Flow.from_client_secrets_file(
    GOOGLE_CLIENT_SECRET_FILE,
    scopes=["openid", "email", "profile"],
    redirect_uri="http://localhost:8080/callback"
)

# נתיב התחברות
@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return redirect(authorization_url)

# נתיב callback של גוגל
@app.route('/callback')
def callback():
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    request_session = google.auth.transport.requests.Request()
    id_info = .oauth2.id_token.verify_oauth2_token(
        credentials.id_token, request_session
    )

    user_id = id_info['sub']
    user_email = id_info['email']
    user_name = id_info.get('name', user_email)

    user = User(user_id, user_name, user_email)
    users[user_id] = user
    login_user(user)

    return redirect(url_for("home"))

# נתיב התנתקות
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

# שינוי נתיב הבית כך שידרוש התחברות
@app.route('/')
@login_required
def home():
    return render_template('index.html', user=current_user)

# הפעלת השרת
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

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
