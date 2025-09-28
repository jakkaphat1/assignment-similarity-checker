"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./login.module.css";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to login");
      }


      // เมื่อ Login สำเร็จ เราจะได้รับ access_token กลับมา
      // เก็บ Token นี้ไว้ใน localStorage ของเบราว์เซอร์
      if (data.access_token) {
        localStorage.setItem("access_token", data.access_token);
        alert("Login successful! Redirecting to dashboard...");
        router.push("/dashboard");
      } else {
        throw new Error("Access token not found in response");
      }
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <form onSubmit={handleSubmit} className={styles.form}>
        <h1>Login</h1>
        
        {error && <p className={styles.error}>{error}</p>}
        
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
            className={styles.input}
          />
        </div>
        
        <button type="submit" disabled={isLoading} className={styles.button}>
          {isLoading ? "Logging In..." : "Login"}
        </button>

        <p className={styles.signupLink}>
          Don't have an account? <Link href="/signup">Sign Up</Link>
        </p>
      </form>
    </div>
  );
}