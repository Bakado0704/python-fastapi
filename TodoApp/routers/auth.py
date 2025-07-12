from typing import Annotated # Annotated=型を注入する
from fastapi import APIRouter, Depends, HTTPException # APIRouter=エンドポイントをグループ化 Depends=依存性注入する関数 HTTPException=エラーレスポンス
from pydantic import BaseModel # BaseModel=リクエストボディをつくる
from sqlalchemy.orm import Session # セッションという型
from models import Users # models.pyで定義したUsers
from passlib.context import CryptContext # パスワードのハッシュ化するためのクラス
from database import SessionLocal # database.pyで定義したSessionLocal
from starlette import status # ステータスコードの定数群
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer # ログイン認証時に使われるセキュリティユーティリティ
from jose import jwt, JWTError # iwt=エンコードデコードのためのライブラリ JWT=JWTの検証・デコード時に発生するエラー
from datetime import timedelta, datetime, timezone #timedelta=時間の差を表すクラス datetime=日付と時刻を表すクラス timezone=タイムゾーンを表すクラス

router = APIRouter( # 画面を開いた時にAuthで分類する
    prefix="/auth", # すべてのURLを /auth からスタートさせる
    tags=["auth"] # Swagger UIの分類
)

SECRET_KEY = "c470eff2457bfb59b43bb761d5ee93fcdecfe6a297c94353ab1c5332b5358a97" #openssl rand -hex 32で生成されたSECRET_KEY
ALGOLITHM = "HS256" # HS256のハッシュを使う


bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # ハッシュ化したパスワードと普通のパスワードを比較するためのインスタンス
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="token") # ログイン後に使うトークンを取得・検証するためのインスタンス


class CreateUserRequest(BaseModel): # エンドポイントに渡されるリクエストボディの型
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str

class Token(BaseModel): # エンドポイントに渡されるリクエストボディの型
    access_token: str
    token_type: str

def get_db():
    db = SessionLocal() # セッションを開始
    try:
        yield db # 呼び出し元（API関数）にセッションを渡す
    finally:
        db.close() # 処理終了後に必ず接続を閉じる

db_dependency = Annotated[Session, Depends(get_db)] # Annotatedを用いて、get_dbの型をSession型として注入する、それをdbの型としてdb_dependencyとする


def authenticate_user(username: str, password: str, db): 
    user = db.query(Users).filter(Users.username == username).first()
    if not user: # ユーザが存在しないならば
        return False
    if not bcrypt_context.verify(password, user.hashed_password): # ハッシュ化されたuser.hashed_passwordとハッシュ化前のpasswordが合致しないならば
        return False
    return user #上記のif文に引っ掛からなければuserを返す


def create_access_token(username: str, user_id: int, expires_delta: timedelta): # timedeltaは時間の期間を表すクラス
    encode = {"sub": username, "id": user_id} # JWTのペイロードに含めるデータを辞書で定義
    expires = datetime.now(timezone.utc) + expires_delta # 現在時刻に有効期限（期間）を足して、有効期限の日時を作成
    encode.update({"exp": expires}) # timedeltaは時間の期間を表すクラス
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGOLITHM) # encodeとSECRET_KEYを組み合わせたものをエンコードしたtokenを返す


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]): # Annotatedを用いてstr型のoauth2_bearerを注入したtokenを引数とした、get_current_userの関数
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # tokenをSECRET_KEYとALGORITHMからデコードする
        username: str = payload.get("sub") # payloadからsubを取り出す
        user_id: int = payload.get("id") # payloadからidを取り出す
        if username is None or user_id is None: #もしsubとidどちらか一方でも存在しなければ
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, # 401エラーを返し、
                                detail="Could not validate user") # メッセージとしてCould not validate userも返す
        
        return {"username": username, "id": user_id} #もし上記のif文に引っ掛からなければusernameとidを返す
    except JWTError: # もし上記の過程でエラーが起これば、
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, # 401エラーを返し、
                                detail="Could not validate user") # メッセージとしてCould not validate userも返す


@router.post("/auth", status_code=status.HTTP_201_CREATED) # authのクラスの定義、成功すれば201を返す
async def create_user(db: db_dependency,create_user_request: CreateUserRequest): #create_user_requestの入力値を定義
    create_user_model = Users( # モデルを作成
        email=create_user_request.email,
        username=create_user_request.username,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        role=create_user_request.role,
        hashed_password=bcrypt_context.hash(create_user_request.password),
        is_active=True
    )

    db.add(create_user_model)
    db.commit()


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
                                 db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        return "Failed Authentication"
    
    token = create_access_token(user.username, user.id, timedelta(minutes=20))

    return {"access_token": token, "token_type": "bearer"}