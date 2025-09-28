from fastapi import APIRouter, Form, HTTPException, Depends, Header
from typing import Optional

from supabase_client import supabase
from schemas import UserCreate, UserLogin

# สร้าง router สำหรับ authentication
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


async def get_current_user(authorization: Optional[str] = Header(None)):
    """ตรวจสอบ JWT จาก Header และดึงข้อมูลจาก Supabase"""

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.split(" ")[1]  # เอา Bearer token ออก
    try:
        user_response = supabase.auth.get_user(token)
        return user_response.user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/signup")
async def signup(user_data: UserCreate):
    """เป็น Endpoint สำหรับการสมัครสมาชิก รับข้อมูลแบบ JSON"""
    try:
        res = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
        })
        return {
            "message": "สมัครสมาชิกสำเร็จ", 
            "user_id": res.user.id,
            "email": res.user.email
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(user_data: UserLogin):
    """Endpoint สำหรับการเข้าสู่ระบบ"""
    try:
        res = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        return {
            "message": "ล็อคอินสำเร็จ",
            "access_token": res.session.access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=401, detail="Invalid login credentials")
