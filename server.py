import os,re,json,hmac,urllib.request,urllib.parse,io
from PIL import Image, ImageOps
from flask import Response
from datetime import date
from flask import Flask,request,session,jsonify,send_from_directory
import psycopg
app=Flask(__name__,static_folder='public',static_url_path='')
app.secret_key=os.environ['SECRET_KEY']
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','1')=='1',MAX_CONTENT_LENGTH=21_000_000)
def db(): return psycopg.connect(os.environ['DATABASE_URL'])
with db() as c:
    c.execute('SELECT pg_advisory_xact_lock(824166)')
    c.execute('CREATE TABLE IF NOT EXISTS courses (day date PRIMARY KEY, items jsonb NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS branding (id integer PRIMARY KEY, logo bytea NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS branding_layout (id integer PRIMARY KEY, settings jsonb NOT NULL)')
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
        assert all(isinstance(x,dict) and ((x.get('kind','video')=='video' and re.fullmatch(r'[A-Za-z0-9_-]{11}',x['id'])) or (x.get('kind')=='playlist' and re.fullmatch(r'[A-Za-z0-9_-]{2,150}',x['id']) and (not x.get('thumbnail') or re.fullmatch(r'https://(?:i\.ytimg\.com|img\.youtube\.com)/[A-Za-z0-9_./?=&%-]+',x['thumbnail'])))) and isinstance(x['title'],str) and 0<len(x['title'])<=300 for x in v)
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

@app.get('/api/logo')
def logo():
    with db() as c: row=c.execute('SELECT logo FROM branding WHERE id=1').fetchone()
    if not row: return send_from_directory('public','logo.png',max_age=0)
    return Response(bytes(row[0]),mimetype='image/png',headers={'Cache-Control':'no-store'})
@app.errorhandler(413)
def too_large(e): return jsonify(error='上傳資料超過 20 MB'),413
@app.get('/api/logo/layout')
def logo_layout():
    with db() as c: row=c.execute('SELECT settings FROM branding_layout WHERE id=1').fetchone()
    return jsonify(row[0] if row else dict(width=180,x=0,y=0))
@app.post('/api/logo')
def upload_logo():
    if not session.get('admin'): return jsonify(error='請先登入'),403
    try:
        layout={k:int(request.form.get(k,d)) for k,d in [('width',180),('x',0),('y',0)]}
        if not 80<=layout['width']<=400 or not 0<=layout['x']<=100 or not 0<=layout['y']<=60: raise ValueError()
    except (ValueError,TypeError): return jsonify(error='LOGO 位置或尺寸設定無效'),400
    f=request.files.get('logo'); blob=None
    if f and f.filename:
        try:
            raw=f.read(20_000_001)
            if len(raw)>20_000_000: return jsonify(error='圖片超過 20 MB'),413
            with Image.open(io.BytesIO(raw)) as im:
                if im.format not in ('PNG','JPEG','WEBP'): return jsonify(error='僅支援 PNG、JPEG、WebP'),400
                if im.width*im.height>40_000_000: return jsonify(error='圖片超過 4000 萬像素，請先縮小'),400
                im.thumbnail((1200,600),Image.Resampling.LANCZOS)
                im=ImageOps.exif_transpose(im).convert('RGBA'); im.thumbnail((1200,600))
                out=io.BytesIO(); im.save(out,format='PNG',optimize=True); blob=out.getvalue()
        except Exception:
            app.logger.exception('Logo image processing failed'); return jsonify(error='圖片無法解碼或處理，請確認檔案完整'),400
    try:
        with db() as c:
            if blob is not None: c.execute('INSERT INTO branding VALUES (1,%s) ON CONFLICT(id) DO UPDATE SET logo=excluded.logo',(blob,))
            c.execute('INSERT INTO branding_layout VALUES (1,%s::jsonb) ON CONFLICT(id) DO UPDATE SET settings=excluded.settings',(json.dumps(layout),))
    except Exception:
        app.logger.exception('Logo database write failed'); return jsonify(error='資料庫儲存失敗，請查看 Railway 紀錄'),500
    return jsonify(ok=True)
@app.delete('/api/logo')
def reset_logo():
    if not session.get('admin'): return jsonify(error='請先登入'),403
    with db() as c:
        c.execute('DELETE FROM branding WHERE id=1'); c.execute('DELETE FROM branding_layout WHERE id=1')
    return jsonify(ok=True)
@app.get('/api/playlist')
def playlist():
    if not session.get('admin'): return jsonify(error='請先登入'),403
    i=request.args.get('id',''); k=os.getenv('YOUTUBE_API_KEY','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,150}',i): return jsonify(error='播放清單網址無效'),400
    if not k: return jsonify(error='尚未設定 YOUTUBE_API_KEY，請手動輸入標題'),503
    try:
        url='https://www.googleapis.com/youtube/v3/playlists?'+urllib.parse.urlencode({'part':'snippet,contentDetails','id':i,'key':k})
        with urllib.request.urlopen(url,timeout=12) as r: items=json.load(r)['items']
        if not items: return jsonify(error='找不到公開或可存取的播放清單'),404
        v=items[0]; sn=v['snippet']; thumbs=sn.get('thumbnails',{}); thumb=next((thumbs[x]['url'] for x in ('high','medium','default') if x in thumbs),'')
        if not re.fullmatch(r'https://(?:i\.ytimg\.com|img\.youtube\.com)/[A-Za-z0-9_./?=&%-]+',thumb): thumb=''
        return jsonify(title=sn['title'],thumbnail=thumb,count=v['contentDetails']['itemCount'])
    except Exception: return jsonify(error='播放清單讀取失敗，請確認 API 金鑰、配額及清單權限'),502
