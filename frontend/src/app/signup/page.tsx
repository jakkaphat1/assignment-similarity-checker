"use client"; // บอก Next.js ว่านี่เป็น Client Component เพราะต้องมีการโต้ตอบกับผู้ใช้

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import styles from "./signup.module.css";

export default function SignupPage(){
  const router = useRouter();
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [full_name, setFullName] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); // ป้องกันไม่ให้หน้าเว็บรีเฟรชเอง
    setIsLoading(true);
    setError(null);

    try {
      // ส่ง Request ไปยัง FastAPI Backend
      const response = await fetch("http://127.0.0.1:8000/auth/signup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password , full_name}),
      });

    const data = await response.json();
    
          if (!response.ok) {
        // ถ้า Backend ส่ง error กลับมา (เช่น status 400)
        throw new Error(data.detail || "Something went wrong");
      }

      // ถ้าสมัครสมาชิกสำเร็จ
      alert("Signup successful! Redirecting to login page");
      router.push("/login"); // ไปยังหน้า Login

      } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
 };

  return (
    <div className={styles.container}>
      <form onSubmit={handleSubmit} className={styles.form}>
        <h1>Sign Up</h1>
        
        {error && <p className={styles.error}>{error}</p>}
        
        <div className={styles.inputGroup}>
          <label htmlFor="fullName">Full Name</label>
          <input
            id="fullName"
            type="text"
            value={full_name}
            onChange={(e) => setFullName(e.target.value)}
            required
            className={styles.input}
            
          />
        </div>



        <div className={styles.inputGroup}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className={styles.input}
          />
        </div>
        
        <div className={styles.inputGroup}>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className={styles.input}
          />
        </div>
        
        <button type="submit" disabled={isLoading} className={styles.button}>
          {isLoading ? "Signing Up..." : "Sign Up"}
        </button>
      </form>
    </div>
  );
}










