from pydantic import BaseModel, EmailStr
from typing import Optional
# โมเดลสำหรับรับข้อมูลตอนสมัครสมาชิก


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

# โมเดลสำหรับรับข้อมูลตอนเข้าสู่ระบบ


class UserLogin(BaseModel):
    email: EmailStr
    password: str

# โมเดลสำหรับข้อมูลที่จะส่งกลับไปให้ User (เพื่อความปลอดภัย ไม่ส่ง password กลับไป)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    
#Pydantic class สำหรับผลลัพธ์ของเอกสาร    
class DocumentResult(BaseModel):
    doc_id: str
    status: str
    processing_mode: int
    text_length: Optional[int] = None
    image_count: Optional[int] = None
    removed_text_length: Optional[int] = None
    error: Optional[str] = None    
