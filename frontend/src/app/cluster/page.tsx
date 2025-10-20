"use client";
import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import { Loader2, ArrowLeft, Download } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type CompareItem = {
  doc_1: string;
  doc_2: string;
  combined_score?: number;
  final_score?: number;
};

export default function ClusterPage() {
  const router = useRouter();

  const [threshold, setThreshold] = useState<number>(0.8);
  const [pairs, setPairs] = useState<CompareItem[]>([]);
  const [clusters, setClusters] = useState<string[][]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchingPairs, setFetchingPairs] = useState(false);

  const [token, setToken] = useState<string | null>(null);
  const [batchId, setBatchId] = useState<string | null>(null);

  // โหลด token + last_batch_id จาก sessionStorage
  useEffect(() => {
    const t = sessionStorage.getItem("access_token");
    if (!t) {
      alert("กรุณาเข้าสู่ระบบก่อนใช้งาน");
      router.push("/login");
      return;
    }
    setToken(t);

    const b = sessionStorage.getItem("last_batch_id");
    if (!b) {
      console.warn("ไม่พบ last_batch_id ใน sessionStorage");
    }
    setBatchId(b || null);
  }, [router]);

  const headers = useMemo(
    () => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token]
  );

  // โหลดผล compare ของ batch ล่าสุด (จาก sessionStorage) ถ้ามี
  const loadPairs = async () => {
    if (!token) {
      alert("ไม่พบโทเค็น กรุณาเข้าสู่ระบบใหม่");
      router.push("/login");
      return;
    }
    setFetchingPairs(true);
    try {
      const url = batchId
        ? `${API_BASE}/compare?batch_id=${batchId}`
        : `${API_BASE}/compare`;

      const res = await axios.get<CompareItem[]>(url, { headers });
      const data = Array.isArray(res.data) ? res.data : [];

      setPairs(data);

      if (data.length === 0) {
        alert("ไม่พบผลการเปรียบเทียบของชุดล่าสุด");
      }
    } catch (e: any) {
      if (e?.response?.status === 401) {
        sessionStorage.removeItem("access_token");
        alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
        router.push("/login");
      } else {
        alert(e?.response?.data?.detail || "ดึงผลเปรียบเทียบไม่สำเร็จ");
      }
    } finally {
      setFetchingPairs(false);
    }
  };

  // จัดกลุ่ม
  const handleCluster = async () => {
    if (!token) {
      alert("ไม่พบโทเค็น กรุณาเข้าสู่ระบบใหม่");
      router.push("/login");
      return;
    }

    // ถ้ายังไม่มี pairs ให้ลองโหลดก่อน
    if (pairs.length === 0) {
      await loadPairs();
      if (pairs.length === 0) return;
    }

    setLoading(true);
    try {
      const body = {
        threshold,
        pairs: pairs.map((p) => ({
          doc_1: p.doc_1,
          doc_2: p.doc_2,
          final_score:
            typeof p.final_score === "number"
              ? p.final_score
              : (p.combined_score ?? 0),
        })),
      };

      const res = await axios.post(`${API_BASE}/cluster`, body, { headers });
      setClusters(res.data?.clusters || []);
    } catch (e: any) {
      if (e?.response?.status === 401) {
        sessionStorage.removeItem("access_token");
        alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่");
        router.push("/login");
      } else {
        alert(e?.response?.data?.detail || "เกิดข้อผิดพลาดในการจัดกลุ่ม");
      }
    } finally {
      setLoading(false);
    }
  };

  // แก้ NaN ที่ input: ถ้าผู้ใช้ลบค่าจนว่าง → กลับเป็น 0.8
  const safeSetThreshold = (raw: string) => {
    const v = parseFloat(raw);
    setThreshold(Number.isFinite(v) ? v : 0.8);
  };

  // Export clusters เป็น CSV
  const exportClusters = () => {
    if (clusters.length === 0) {
      alert("ไม่มีข้อมูลกลุ่มให้ Export");
      return;
    }

    // สร้าง CSV โดยแยกแต่ละเอกสารเป็นแถวใหม่
    const csvRows = ["กลุ่ม,ลำดับ,ชื่อเอกสาร"];
    
    clusters.forEach((group, i) => {
      group.forEach((doc, docIndex) => {
        csvRows.push(`${i + 1},${docIndex + 1},${doc}`);
      });
    });

    const csvContent = csvRows.join("\n");
    const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `clusters_${new Date().toISOString().split("T")[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push("/dashboard")}
                className="text-gray-600 hover:text-gray-900"
              >
                <ArrowLeft className="w-6 h-6" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Clustering เอกสาร</h1>
                <p className="text-sm text-gray-600 mt-1">จัดกลุ่มเอกสารที่มีความคล้ายคลึงกัน</p>
              </div>
            </div>
            {clusters.length > 0 && (
              <button
                onClick={exportClusters}
                className="flex items-center px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Controls */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Threshold (0.0 - 1.0)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={Number.isFinite(threshold) ? threshold : ""}
                onChange={(e) => safeSetThreshold(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="0.80"
              />
              <p className="text-xs text-gray-500 mt-1">
                เอกสารที่มีค่าความคล้ายคลึง ≥ threshold จะถูกจัดอยู่กลุ่มเดียวกัน
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                ข้อมูลชุดปัจจุบัน
              </label>
              <div className="bg-gray-50 rounded-md px-4 py-3 border border-gray-200">
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Batch ID:</span>{" "}
                  <span className="text-gray-900">{batchId || "-"}</span>
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  <span className="font-medium">จำนวนคู่เอกสาร:</span>{" "}
                  <span className="text-gray-900">{pairs.length}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 mt-6">
            <button
              onClick={loadPairs}
              disabled={fetchingPairs}
              className="flex items-center px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 disabled:opacity-60 disabled:cursor-not-allowed transition-colors text-black"
              title="ดึงผลเปรียบเทียบจาก /compare"
            >
              {fetchingPairs ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  กำลังดึงผล...
                </>
              ) : (
                "โหลดผลเปรียบเทียบ (ล่าสุด)"
              )}
            </button>

            <button
              onClick={handleCluster}
              disabled={loading || pairs.length === 0}
              className="flex items-center px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  กำลังจัดกลุ่ม...
                </>
              ) : (
                "เริ่ม Clustering"
              )}
            </button>
          </div>
        </div>

        {/* Results */}
        {clusters.length > 0 ? (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              ผลลัพธ์ ({clusters.length} กลุ่ม)
            </h2>
            <div className="space-y-4">
              {clusters.map((group, i) => (
                <div key={i} className="border rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors text-black">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <span className="flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-full text-sm font-bold">
                        {i + 1}
                      </span>
                      <span className="font-medium text-blue-700">
                        กลุ่ม {i + 1}
                      </span>
                    </div>
                    <span className="text-sm text-gray-600">
                      {group.length} ไฟล์
                    </span>
                  </div>
                  <div className="text-sm text-gray-700 pl-11 space-y-1">
                    {group.map((doc, docIndex) => (
                      <div key={docIndex} className="flex items-start">
                        <span className="text-gray-500 mr-2 font-mono">{docIndex + 1})</span>
                        <span>{doc}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
            <p className="text-gray-500">
              ยังไม่มีผลการจัดกลุ่ม — กด "โหลดผลเปรียบเทียบ (ล่าสุด)" แล้ว "เริ่ม Clustering"
            </p>
          </div>
        )}
      </div>
    </div>
  );
}