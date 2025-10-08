import { redirect } from 'next/navigation';

export default function HomePage() {
  // สั่งให้ redirect (เปลี่ยนเส้นทาง) ไปยังหน้า /login ทันที
  redirect('/login');

  // ไม่ต้องแสดงผลอะไร เพราะจะถูกส่งต่อไปก่อน
  return null;
}