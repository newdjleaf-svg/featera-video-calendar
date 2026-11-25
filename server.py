import os,re,json,hmac,urllib.request,urllib.parse
from datetime import date
from flask import Flask,request,session,jsonify,send_from_directory
import psycopg
app=Flask(__name__,static_folder='public',static_url_path='')
app.secret_key=os.environ['SECRET_KEY']
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','1')=='1',MAX_CONTENT_LENGTH=2_000_000)
def db(): return psycopg.connect(os.environ['DATABASE_URL'])
with db() as c: c.execute('CREATE TABLE IF NOT EXISTS courses (day date PRIMARY KEY, items jsonb NOT NULL)')
@app.get('/')
def home(): return send_from_directory('public','index.html')
@app.get('/health')
def health(): return 'ok'
@app.get('/api/session')
def status(): return jsonify(admin=bool(session.get('admin')))
@app.post('/api/login')
def login():
    p=request.get_json(silent=True) or {}; u=str(p.get('username','')); pw=str(p.get('password',''))
    if hmac.compare_digest(u.encode(),os.environ['ADMIN_USERNAME'].encode()) and hmac.compare_digest(pw.encode(),os.environ['ADMIN_PASSWORD'].encode()):
        session.clear(); session['admin']=True; return jsonify(ok=True)
    return jsonify(error='帳號或密碼錯誤'),401
@app.post('/api/logout')
def logout(): session.clear(); return jsonify(ok=True)
@app.get('/api/courses')
def courses():
    with db() as c: return jsonify({str(d):v for d,v in c.execute('SELECT day,items FROM courses')})
@app.put('/api/courses/<day>')
def save(day):
    if not session.get('admin'): return jsonify(error='請先登入'),403
    try:
        d=date.fromisoformat(day); v=request.get_json(); assert isinstance(v,list) and len(v)<=500
        assert all(isinstance(x,dict) and re.fullmatch(r'[A-Za-z0-9_-]{11}',x['id']) and isinstance(x['title'],str) and 0<len(x['title'])<=300 for x in v)
    except Exception: return jsonify(error='資料格式錯誤'),400
    with db() as c:
        if v: c.execute('INSERT INTO courses VALUES (%s,%s::jsonb) ON CONFLICT(day) DO UPDATE SET items=excluded.items',(d,json.dumps(v)))
        else: c.execute('DELETE FROM courses WHERE day=%s',(d,))
    return jsonify(ok=True)
@app.get('/api/video')
@app.get('/api/holidays')
def external():
    try:
        if request.path.endswith('video'):
            i=request.args.get('id',''); assert re.fullmatch(r'[A-Za-z0-9_-]{11}',i)
            url='https://www.youtube.com/oembed?'+urllib.parse.urlencode({'url':'https://www.youtube.com/watch?v='+i,'format':'json'})
        else:
            y=request.args.get('year',''); assert re.fullmatch(r'20\d{2}',y)
            url='https://cdn.jsdelivr.net/gh/ruyut/TaiwanCalendar/data/'+y+'.json'
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=12) as r: data=json.load(r)
        return jsonify({'title':data['title'],'thumbnail':data['thumbnail_url']} if request.path.endswith('video') else data)
    except Exception: return jsonify(error='外部資料暫時無法取得'),502
