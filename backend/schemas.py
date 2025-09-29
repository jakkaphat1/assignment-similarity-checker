from pydantic import BaseModel, EmailStr

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