"use client";

import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { 
  Upload, 
  FileText, 
  Image as ImageIcon, 
  Settings,
  Play,
  Trash2,
  Download,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  BarChart3,
  RefreshCw,
  Info,
  Eye,
} from 'lucide-react'


interface DocumentResult {
  doc_id: string
  status: string
  processing_mode: number
  text_length?: number
  image_count?: number
  removed_text_length?: number
  error?: string
}

interface ComparisonResult {
  doc_1: string
  doc_2: string
  combined_score: number
  text_similarity: number
  semantic_similarity: number
  lexical_similarity: number
  image_similarity: number
  image_cosine_avg: number
  image_phash_avg: number
  matched_images: number
  total_images: number
  level: string
  processing_mode: number
}

interface Stats {
  text_embeddings: {
    total_vector_count: number
    dimension: number
    index_fullness: number
  }
  image_embeddings: {
    total_vector_count: number
    dimension: number
    index_fullness: number
  }
  total_documents: number
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

export default function DashboardPage() {


  // handle access token
  const router = useRouter();
  // State สำหรับ Authentication
  const [isLoading, setIsLoading] = useState(true);

  const [files, setFiles] = useState<File[]>([])
  const [templateFile, setTemplateFile] = useState<File | null>(null)
  const [processingMode, setProcessingMode] = useState<number>(1)
  const [useTemplate, setUseTemplate] = useState<boolean>(false)
  // const [isUploading, setIsUploading] = useState<boolean>(false)
  
  const [isComparing, setIsComparing] = useState<boolean>(false)
  const [uploadResults, setUploadResults] = useState<DocumentResult[]>([])
  const [comparisonResults, setComparisonResults] = useState<ComparisonResult[]>([])
  const [documents, setDocuments] = useState<string[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [showStats, setShowStats] = useState<boolean>(false)

  // Preview PDF 
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewSrc, setPreviewSrc] = useState<string | null>(null)
  const [previewName, setPreviewName] = useState<string>("")
  const [previewIsBlob, setPreviewIsBlob] = useState(false)
  const [previewBlobUrl, setPreviewBlobUrl] = useState<string | null>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const pdfFiles = acceptedFiles.filter(file => file.type === 'application/pdf')
    if (pdfFiles.length !== acceptedFiles.length) {
      alert('กรุณาอัปโหลดเฉพาะไฟล์ PDF เท่านั้น')
    }
    setFiles(prev => [...prev, ...pdfFiles])
  }, [])

  const onTemplateDrop = useCallback((acceptedFiles: File[]) => {
    const pdfFile = acceptedFiles.find(file => file.type === 'application/pdf')
    if (pdfFile) {
      setTemplateFile(pdfFile)
    } else {
      alert('กรุณาอัปโหลดไฟล์ PDF สำหรับ Template')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: true
  })

  const { 
    getRootProps: getTemplateRootProps, 
    getInputProps: getTemplateInputProps, 
    isDragActive: isTemplateDragActive 
  } = useDropzone({
    onDrop: onTemplateDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false
  })

  const openPreviewFromFile = (file: File) => {
    const url = URL.createObjectURL(file)
    setPreviewSrc(url)
    setPreviewBlobUrl(url)
    setPreviewIsBlob(true)
    setPreviewName(file.name)
    setPreviewOpen(true)
  }

  const openPreviewRemote = (docId: string) => {
    setPreviewSrc(`${API_BASE}/preview/${docId}`)
    setPreviewIsBlob(false)
    setPreviewBlobUrl(null)
    setPreviewName(docId)
    setPreviewOpen(true)
  }

  const closePreview = () => {
    if (previewIsBlob && previewBlobUrl) URL.revokeObjectURL(previewBlobUrl)
    setPreviewOpen(false)
    setPreviewSrc(null)
    setPreviewBlobUrl(null)
    setPreviewIsBlob(false)
  }







  // ==========================================================
  // ส่วนที่ 2: useEffect สำหรับจัดการ Logic ที่ต้องทำครั้งเดียว
  // ==========================================================
  useEffect(() =>{
    const token = localStorage.getItem('access_token');

    if (!token){
      alert('กรุณาเข้าสู่ระบบก่อนใช้งาน');
      router.push('/login');
    }else{
      setIsLoading(false);
    }
  }, [router]);



  // ==========================================================
  // ส่วนที่ 3: ฟังก์ชัน Helper และ Event Handlers
  // ==========================================================
  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const removeTemplateFile = () => {
    setTemplateFile(null)
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      alert('กรุณาเลือกไฟล์ PDF อย่างน้อย 1 ไฟล์')
      return
    }

    if (useTemplate && !templateFile) {
      alert('กรุณาอัปโหลดไฟล์ Template')
      return
    }

    setIsLoading(true)
    setUploadResults([])
    
    try {
      const formData = new FormData()
      
      files.forEach(file => {
        formData.append('files', file)
      })
      
      formData.append('processing_mode', processingMode.toString())
      formData.append('use_template', useTemplate.toString())
      
      if (useTemplate && templateFile) {
        formData.append('template_file', templateFile)
      }

      const response = await axios.post(`${API_BASE}/upload-pdfs`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 300000 // 5 minutes timeout
      })

      setUploadResults(response.data.results)
      
      // Fetch updated document list
      await fetchDocuments()
      
    } catch (error: any) {
      console.error('Upload error:', error)
      const errorMsg = error.response?.data?.detail || 'เกิดข้อผิดพลาดในการอัปโหลดไฟล์'
      alert(`ข้อผิดพลาด: ${errorMsg}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCompare = async () => {
    if (documents.length < 2) {
      alert('ต้องมีอย่างน้อย 2 เอกสารเพื่อทำการเปรียบเทียบ')
      return
    }

    setIsComparing(true)
    setComparisonResults([])
    
    try {
      const response = await axios.get(`${API_BASE}/compare`, {
        timeout: 300000 // 5 minutes timeout
      })
      setComparisonResults(response.data.comparisons)
    } catch (error: any) {
      console.error('Comparison error:', error)
      const errorMsg = error.response?.data?.detail || 'เกิดข้อผิดพลาดในการเปรียบเทียบ'
      alert(`ข้อผิดพลาด: ${errorMsg}`)
    } finally {
      setIsComparing(false)
    }
  }

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE}/documents`)
      setDocuments(response.data.documents)
    } catch (error) {
      console.error('Error fetching documents:', error)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/stats`)
      setStats(response.data)
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  const handleClearAll = async () => {
    if (!confirm('คุณแน่ใจหรือไม่ที่จะลบเอกสารทั้งหมด?')) 
      return
    
    try {
      await axios.delete(`${API_BASE}/documents`)
      setDocuments([])
      setUploadResults([])
      setComparisonResults([])
      setFiles([])
      setTemplateFile(null)
      setStats(null)
      alert('ลบเอกสารทั้งหมดเรียบร้อยแล้ว')
    } catch (error: any) {
      console.error('Clear error:', error)
      alert('เกิดข้อผิดพลาดในการลบเอกสาร')
    }
  }

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'เหมือนมาก': return 'text-red-600 bg-red-50 border-red-200'
      case 'คล้ายสูง': return 'text-orange-600 bg-orange-50 border-orange-200'
      case 'คล้ายระดับกลาง': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'คล้ายน้อย': return 'text-blue-600 bg-blue-50 border-blue-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getModeText = (mode: number) => {
    switch (mode) {
      case 1: return 'ข้อความเท่านั้น'
      case 2: return 'รูปภาพเท่านั้น'
      case 3: return 'ข้อความ + รูปภาพ'
      default: return 'ไม่ระบุ'
    }
  }

  const getModeIcon = (mode: number) => {
    switch (mode) {
      case 1: return <FileText className="w-4 h-4" />
      case 2: return <ImageIcon className="w-4 h-4" />
      case 3: return <Settings className="w-4 h-4" />
      default: return <Settings className="w-4 h-4" />
    }
  }

  const formatScore = (score: number) => {
    return (score * 100).toFixed(2) + '%'
  }

  const exportResults = () => {
    if (comparisonResults.length === 0) {
      alert('ไม่มีผลการเปรียบเทียบให้ Export')
      return
    }

    const csvContent = [
      ['เอกสาร 1', 'เอกสาร 2', 'คะแนนรวม', 'ความคล้ายข้อความ', 'ความคล้าย Semantic', 'ความคล้าย Lexical', 'ความคล้ายรูปภาพ', 'รูปภาพที่ตรงกัน', 'รูปภาพทั้งหมด', 'ระดับความคล้าย'],
      ...comparisonResults.map(result => [
        result.doc_1,
        result.doc_2,
        formatScore(result.combined_score),
        formatScore(result.text_similarity),
        formatScore(result.semantic_similarity),
        formatScore(result.lexical_similarity),
        formatScore(result.image_similarity),
        result.matched_images,
        result.total_images,
        result.level
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `plagiarism_results_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }  

  // ==========================================================
  // ส่วนที่ 4: เงื่อนไขการแสดงผล (Conditional Rendering)
  // ==========================================================
  if (isLoading){
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-10 h-10 text-gray-400 mx-auto animate-spin" />
          <p className="mt-4 text-gray-600">กำลังโหลด...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">ระบบตรวจจับการคัดลอก PDF</h1>
              <p className="text-sm text-gray-600 mt-1">PDF Plagiarism Detection System</p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={fetchStats}
                className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <BarChart3 className="w-4 h-4 mr-2" />
                สถิติ
              </button>
              <button
                onClick={handleClearAll}
                className="flex items-center px-3 py-2 text-sm font-medium text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                ลบทั้งหมด
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Upload Section */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">อัปโหลดไฟล์ PDF</h2>
              
              {/* Processing Mode Selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-3">โหมดการประมวลผล</label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { mode: 1, icon: FileText, label: 'ข้อความเท่านั้น', desc: 'วิเคราะห์เฉพาะเนื้อหาข้อความ' },
                    { mode: 2, icon: ImageIcon, label: 'รูปภาพเท่านั้น', desc: 'วิเคราะห์เฉพาะรูปภาพและแผนภาพ' },
                    { mode: 3, icon: Settings, label: 'ข้อความ + รูปภาพ', desc: 'วิเคราะห์ทั้งข้อความและรูปภาพ' }
                  ].map(({ mode, icon: Icon, label, desc }) => (
                    <button
                      key={mode}
                      onClick={() => setProcessingMode(mode)}
                      className={`p-4 border-2 rounded-lg text-left transition-colors ${
                        processingMode === mode
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center mb-2">
                        <Icon className="w-5 h-5 mr-2" />
                        <span className="font-medium text-sm">{label}</span>
                      </div>
                      <p className="text-xs text-gray-600">{desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Template Option */}
              <div className="mb-6">
                <div className="flex items-center mb-3">
                  <input
                    type="checkbox"
                    id="useTemplate"
                    checked={useTemplate}
                    onChange={(e) => setUseTemplate(e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="useTemplate" className="ml-2 text-sm font-medium text-gray-700">
                    ใช้ไฟล์ Template เพื่อลบข้อความซ้ำ
                  </label>
                </div>
                
                {useTemplate && (
                  <div className="mt-3">
                    <div
                      {...getTemplateRootProps()}
                      className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
                        isTemplateDragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50'
                      }`}
                    >
                      <input {...getTemplateInputProps()} />
                      {templateFile ? (
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            <FileText className="w-5 h-5 text-blue-600 mr-2" />
                            <span className="text-sm text-gray-700">{templateFile.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {/* NEW 👇 พรีวิว Template */}
                            <button
                              onClick={(e) => { e.stopPropagation(); openPreviewFromFile(templateFile) }}
                              className="text-gray-600 hover:text-gray-900"
                              title="ดูพรีวิว Template"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              removeTemplateFile()
                            }}
                            className="text-red-600 hover:text-red-700"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      ) : (
                        <div>
                          <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                          <p className="text-sm text-gray-600">
                            ลากไฟล์ Template PDF มาที่นี่ หรือคลิกเพื่อเลือกไฟล์
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* File Drop Zone */}
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  isDragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-white'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                {isDragActive ? (
                  <p className="text-lg text-blue-600">วางไฟล์ PDF ที่นี่...</p>
                ) : (
                  <div>
                    <p className="text-lg text-gray-600 mb-2">ลากไฟล์ PDF มาที่นี่</p>
                    <p className="text-sm text-gray-500">หรือคลิกเพื่อเลือกไฟล์ (รองรับหลายไฟล์)</p>
                  </div>
                )}
              </div>

              {/* Selected Files */}
              {files.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">ไฟล์ที่เลือก ({files.length} ไฟล์)</h3>
                  <div className="space-y-2">
                    {files.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center">
                          <FileText className="w-5 h-5 text-blue-600 mr-3" />
                          <div>
                            <p className="text-sm font-medium text-gray-900">{file.name}</p>
                            <p className="text-xs text-gray-500">
                              {(file.size / (1024 * 1024)).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {/* NEW 👇 ปุ่มดูพรีวิวไฟล์ที่เลือก */}
                          <button
                            onClick={() => openPreviewFromFile(file)}
                            className="text-gray-600 hover:text-gray-900"
                            title="ดูพรีวิว"
                          >
                            <Eye className="w-5 h-5" />
                          </button>
                        <button
                          onClick={() => removeFile(index)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <XCircle className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Upload Button */}
              <div className="mt-6">
                <button
                  onClick={handleUpload}
                  disabled={files.length === 0 || isLoading || (useTemplate && !templateFile)}
                  className="w-full flex items-center justify-center px-4 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      กำลังประมวลผล...
                    </>
                  ) : (
                    <>
                      <Upload className="w-5 h-5 mr-2" />
                      อัปโหลดและประมวลผล
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Upload Results */}
            {uploadResults.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border p-6 mt-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">ผลการประมวลผล</h2>
                <div className="space-y-3">
                  {uploadResults.map((result, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          {result.status === 'processed' ? (
                            <CheckCircle className="w-5 h-5 text-green-600 mr-3" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-600 mr-3" />
                          )}
                          <div>
                            <h3 className="font-medium text-gray-900">{result.doc_id}</h3>
                            <div className="flex items-center text-sm text-gray-600 mt-1">
                              {getModeIcon(result.processing_mode)}
                              <span className="ml-1">{getModeText(result.processing_mode)}</span>
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          {result.status === 'processed' ? (
                            <span className="px-2 py-1 text-xs font-medium text-green-800 bg-green-100 rounded-full">
                              สำเร็จ
                            </span>
                          ) : (
                            <span className="px-2 py-1 text-xs font-medium text-red-800 bg-red-100 rounded-full">
                              ผิดพลาด
                            </span>
                          )}
                        </div>
                      </div>
                      
                      {result.status === 'processed' && (
                        <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          {result.text_length !== undefined && (
                            <div>
                              <span className="text-gray-500">ความยาวข้อความ:</span>
                              <span className="ml-1 font-medium">{result.text_length.toLocaleString()} ตัวอักษร</span>
                            </div>
                          )}
                          {result.image_count !== undefined && (
                            <div>
                              <span className="text-gray-500">จำนวนรูปภาพ:</span>
                              <span className="ml-1 font-medium">{result.image_count} รูป</span>
                            </div>
                          )}
                          {result.removed_text_length !== undefined && result.removed_text_length > 0 && (
                            <div>
                              <span className="text-gray-500">ข้อความที่ลบ:</span>
                              <span className="ml-1 font-medium">{result.removed_text_length.toLocaleString()} ตัวอักษร</span>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {result.error && (
                        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
                          <p className="text-sm text-red-800">{result.error}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Documents List */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">เอกสารในระบบ</h2>
                <button
                  onClick={fetchDocuments}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              
              {documents.length > 0 ? (
                <div className="space-y-2">
                  {documents.map((doc, index) => (
                    <div key={index} className="flex items-center p-2 bg-gray-50 rounded">
                      <FileText className="w-4 h-4 text-gray-600 mr-2" />
                      <span className="text-sm text-gray-900 truncate">{doc}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">ยังไม่มีเอกสารในระบบ</p>
              )}
            </div>

            {/* Stats Panel */}
            {stats && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">สถิติระบบ</h2>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">เอกสารทั้งหมด</span>
                      <span className="font-medium">{stats.total_documents}</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Text Embeddings</span>
                      <span className="font-medium">{stats.text_embeddings.total_vector_count}</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Image Embeddings</span>
                      <span className="font-medium">{stats.image_embeddings.total_vector_count}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Compare Button */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <button
                onClick={handleCompare}
                disabled={documents.length < 2 || isComparing}
                className="w-full flex items-center justify-center px-4 py-3 border border-transparent text-base font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {isComparing ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    กำลังเปรียบเทียบ...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5 mr-2" />
                    เริ่มเปรียบเทียบ
                  </>
                )}
              </button>
              
              {documents.length < 2 && (
                <p className="text-xs text-gray-500 text-center mt-2">
                  ต้องมีอย่างน้อย 2 เอกสาร
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Comparison Results */}
        {comparisonResults.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border p-6 mt-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900">ผลการเปรียบเทียบ</h2>
              <button
                onClick={exportResults}
                className="flex items-center px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </button>
            </div>
            
            <div className="space-y-4">
              {comparisonResults
                .sort((a, b) => b.combined_score - a.combined_score)
                .map((result, index) => (
                  <div key={index} className="border rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-4">
                        <h3 className="text-lg font-medium text-gray-900">
                          ไฟล์ {result.doc_1} vs {result.doc_2}
                        </h3>
                        <span className={`px-3 py-1 text-sm font-medium rounded-full border ${getLevelColor(result.level)}`}>
                          {result.level}
                        </span>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-gray-900">
                          {formatScore(result.combined_score)}
                        </div>
                        <div className="text-sm text-gray-500">คะแนนรวม</div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center">
                        <div className="text-lg font-semibold text-blue-600">
                          {formatScore(result.text_similarity)}
                        </div>
                        <div className="text-sm text-gray-600">ความคล้ายข้อความ</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-lg font-semibold text-purple-600">
                          {formatScore(result.semantic_similarity)}
                        </div>
                        <div className="text-sm text-gray-600">Semantic</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-lg font-semibold text-indigo-600">
                          {formatScore(result.lexical_similarity)}
                        </div>
                        <div className="text-sm text-gray-600">Lexical</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-lg font-semibold text-green-600">
                          {formatScore(result.image_similarity)}
                        </div>
                        <div className="text-sm text-gray-600">ความคล้ายรูปภาพ</div>
                      </div>
                    </div>
                    
                    {result.total_images > 0 && (
                      <div className="mt-4 pt-4 border-t">
                        <div className="text-sm text-gray-600">
                          <span className="font-medium">รูปภาพที่ตรงกัน:</span> {result.matched_images} / {result.total_images} รูป
                          {result.image_cosine_avg > 0 && (
                            <>
                              {' | '}
                              <span className="font-medium">Cosine Avg:</span> {formatScore(result.image_cosine_avg)}
                            </>
                          )}
                          {result.image_phash_avg > 0 && (
                            <>
                              {' | '}
                              <span className="font-medium">pHash Avg:</span> {formatScore(result.image_phash_avg)}
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>

     {/* Modal Preview PDF */}
      {previewOpen && previewSrc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-white w-[50vw] max-w-[1000px] h-[85vh] rounded-lg shadow-xl overflow-hidden flex flex-col"> {/* CHANGED */}
            <div className="px-4 py-2 border-b flex items-center justify-between">
              <h3 className="font-medium text-gray-900 truncate">{previewName}</h3>
              <button onClick={closePreview} className="text-gray-600 hover:text-gray-900">
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            <iframe
              src={previewSrc}
              title="PDF Preview"
              className="w-full h-full"
            />
          </div>
        </div>
      )}
    </div>
  )
}