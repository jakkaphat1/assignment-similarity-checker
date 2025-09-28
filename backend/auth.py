from fastapi import APIRouter, Form, HTTPException, Depends, Header
from typing import Optional

from supabase_client import supabase


#สร้าง router สำหรับ authentication
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

async def get_current_user(authorization: Optional[str] = Header(None)):
    """ตรวจสอบ JWT จาก Header และดึงข้อมูลจาก Supabase"""
    
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
   
    token = authorization.split(" ")[1]  #เอา Bearer token ออก
    try:
        user_response = supabase.auth.get_user(token)
        return user_response.user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@router.post("/signup")
async def signup(email: str = Form(...), password: str = Form(...)): #(...) คือ การหาข้อมูลที่มาจาก Form data
    """เป็น Endpoint สำหรับการสมัครสมาชิก"""
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        return {
            "message" : "สมัครสมาชิกสำเร็จ",
            "user_id": res.user.id,
            "email": res.user.email
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))