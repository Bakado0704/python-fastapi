from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Path, Depends, HTTPException
from starlette import status
from models import Todos
from database import SessionLocal


router = APIRouter()




def get_db():
    db = SessionLocal() # セッションを開始
    try:
        yield db # 呼び出し元（API関数）にセッションを渡す
    finally:
        db.close() # 処理終了後に必ず接続を閉じる


db_dependency = Annotated[Session, Depends(get_db)] # dbの型


class TodoRequest(BaseModel): # 関数に渡すTodoの型を定義
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool


@router.get("/", status_code=status.HTTP_200_OK) # 関数定義、うまくいけば200を返す
async def read_all(db: db_dependency): # DBを入力
    return db.query(Todos).all() # db.query(Todos).all()で全件取得


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK) # 関数定義、うまくいけば200を返す
async def read_todo(db: db_dependency, todo_id: int = Path(gt=0)): # DBとidを入力
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first() #DBの中から該当するデータを取得
    if todo_model is not None: # もしデータが空でなければ
        return todo_model
    raise HTTPException(status_code=404, detail="Todo not found.") # もしデータが空であれば


@router.post("/todo", status_code=status.HTTP_201_CREATED) # 関数定義、うまくいけば201を返す
async def create_todo(db: db_dependency, todo_request: TodoRequest): # dbとTodoを入力
    todo_model = Todos(**todo_request.model_dump()) #modelの中に入れ、BaseModelの型なのでmodel_dumpで中をこじ開け、todo_modelを手にいれる

    db.add(todo_model) # todo_modelを追加する
    db.commit()


@router.put("/todo/{todo_id}", status_code= status.HTTP_204_NO_CONTENT) # 関数定義、うまくいけば204を返す
async def update_todo(db: db_dependency, # dbとTodoとidを入力
                       todo_request: TodoRequest, 
                       todo_id: int = Path(gt=0)):
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first() #idと合致する配列の中の最初の要素であるtodo_modelを手にいれる
    if todo_model is None: # もしデータが空であれば
        raise HTTPException(status_code=404, detail="Todo not found.") # 404エラーを返す
    
    todo_model.title = todo_request.title #todo_modelのtitleを入力値のtodo_requestに置き換え
    todo_model.description = todo_request.description #todo_modelのdescriptionを入力値のtodo_requestに置き換え
    todo_model.priority = todo_request.priority #todo_modelのpriorityを入力値のtodo_requestに置き換え
    todo_model.complete = todo_request.complete #todo_modelのcompleteを入力値のtodo_requestに置き換え

    db.add(todo_model) # todo_modelを追加する
    db.commit()


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT) # 関数定義、うまくいけば204を返す
async def delete_todo(db: db_dependency, todo_id: int = Path(gt=0)): # dbとidを入力
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first() #idと合致する配列の中の最初の要素であるtodo_modelを手にいれる
    if todo_model is None: # もしデータが空であれば
        raise HTTPException(status_code=404, detail="Todo not found.") # 404エラーを返す
    
    db.query(Todos).filter(Todos.id == todo_id).delete() #Todosの配列の中から該当するidのデータを削除する

    db.commit()