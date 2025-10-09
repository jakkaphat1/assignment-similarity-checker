from supabase import create_client, Client
from utils import to_ascii_id
from supabase_client import supabase
from auth import get_current_user
from auth import router as auth_router
from utils import cleanup_temp_dir, validate_pdf_files
from vector_db import VectorDBManager
from embedding import EmbeddingManager
from pdf_processing import PDFProcessor
from contextlib import asynccontextmanager
from pathlib import Path
import shutil
import tempfile
import os
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, Header
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
import uvicorn
from fastapi.responses import JSONResponse
import io
import fitz
from dotenv import load_dotenv
from supabase_client import supabase, supabase_admin
from typing import List
from schemas import DocumentResult
from auth import get_current_user
load_dotenv()

app = FastAPI()


# Initialize FastAPI app
app = FastAPI(
    title="PDF Plagiarism Detection API",
    version="2.0.0",
    description="API for detecting plagiarism in PDF documents using text and image analysis"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

# Global managers
pdf_processor = None
embedding_manager = None
vector_db_manager = None


# @app.get("/login")
# async def login():
#     """Simple login endpoint (placeholder)"""
#     return {"message": "Login successful"}


@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup"""
    global pdf_processor, embedding_manager, vector_db_manager

    print("Starting PDF Plagiarism Detection API...")

    try:
        # Initialize embedding manager
        print("Loading embedding models")
        embedding_manager = EmbeddingManager()
        await embedding_manager.initialize()

        # Initialize vector database
        print("Connecting to vector database")
        vector_db_manager = VectorDBManager()
        await vector_db_manager.initialize()

        # Initialize PDF processor
        print("Setting up PDF processor")
        pdf_processor = PDFProcessor(embedding_manager)

        print("All components is initialized")
    except Exception as e:
        print(f"Error during startup: {e}")
        raise e


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "PDF Plagiarism Detection API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "api": "healthy",
        "embedding_manager": "loaded" if embedding_manager and embedding_manager.is_ready() else "not ready",
        "vector_db": "connected" if vector_db_manager and vector_db_manager.is_connected() else "disconnected",
        "pdf_processor": "ready" if pdf_processor else "not ready"
    }


# /upload to Supabase bucket
# @app.post("/upload")
# async def upload_files_and_save_to_supabase(
#     files: List[UploadFile] = File(...),
#     current_user=Depends(get_current_user)
# ):
#     user_id = current_user.id
#     bucket_name = "pdf-files"
#     results = []

#     temp_dir = tempfile.mkdtemp()
#     try:
#         for file in files:
#             file_path = Path(temp_dir) / file.filename

#             with open(file_path, "wb") as buffer:
#                 shutil.copyfileobj(file.file, buffer)

#             with open(file_path, "rb") as f:
#                 file_content = f.read()

#             # Upload ขึ้น Supabase bucket
#             supabase.storage.from_(bucket_name).upload(
#                 path=storage.path,
#                 file=file_content,
#                 file_options={
#                     "content_type": "application/pdf",
#                 }
#             )

#             documents_data = {
#                 "file_name": file.filename,
#                 "doc_id_slug": to_ascii_id(file.filename),
#                 "storage_path": storage_path,
#                 "owner_id": user_id  # <-- จะได้บอกว่าไฟล์นี้เป็นของใคร
#             }

#             # บันทึกข้อมูลลงในตาราง documents ใน supabase
#             db_response = supabase.table(
#                 "documents").insert(documents_data).execute()

#             results.append({
#                 "file_name": file.filename,
#                 "status": "success",
#                 "data": db_response.data[0]

#             })

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")
#     finally:
#         shutil.rmtree(temp_dir)     #<-- ให้ลบ folder tempfile ทิ้งเสมอไม่ว่าจะสำเร็จหรือไม่
#     return {"message": "Files uploaded successfully", "results": results}

# new upload endpoint
# code เดิม
# @app.post("/upload-pdfs")
# async def upload_and_process_pdfs_with_auth(
#     current_user=Depends(get_current_user),
#     # authorization: Optional[str] = Header(None),


#     files: List[UploadFile] = File(...),
#     processing_mode: int = Form(1, description="1=Text, 2=Images, 3=Both"),
#     use_template: bool = Form(False, description="Use template"),
#     template_file: Optional[UploadFile] = File(
#         None, description="Template PDF")
# ):
#     """
#     รับไฟล์, ตรวจสอบสิทธิ์, บันทึกลง Supabase
#     """

#     # current_user = await get_current_user(authorization)
#     user_id = current_user.id
#     bucket_name = "pdf.files"  # <-- ชื่อ Bucket บน Supabase
#     # token = authorization.split(" ")[1]

#     if not pdf_processor or not embedding_manager or not vector_db_manager:
#         raise HTTPException(status_code=503, detail="Service not ready.")
#     if processing_mode not in [1, 2, 3]:
#         raise HTTPException(status_code=400, detail="Invalid processing mode")
#     validate_pdf_files(files)
#     if use_template and not template_file:
#         raise HTTPException(status_code=400, detail="Template file required")

#     temp_dir = tempfile.mkdtemp(prefix="pdf_upload_")
#     try:
#         # supabase.auth.set_session(token)
#         supabase.postgrest.auth(os.environ["SUPABASE_SERVICE_ROLE_KEY"])
#         template_text = ""
#         if use_template and template_file:
#             template_path = os.path.join(temp_dir, template_file.filename)
#             with open(template_path, "wb") as buffer:
#                 shutil.copyfileobj(template_file.file, buffer)
#             template_text = pdf_processor.extract_template_text(template_path)

#         results = []

#         for file in files:
#             file_path_str = os.path.join(temp_dir, file.filename)
#             with open(file_path_str, "wb") as buffer:
#                 file.file.seek(0)
#                 shutil.copyfileobj(file.file, buffer)

#             try:
#                 with open(file_path_str, "rb") as f:
#                     file_content = f.read()
#                 storage_path = f"{user_id}/{file.filename}"

#                 supabase.storage.from_(bucket_name).upload(
#                     path=storage_path,
#                     file=file_content,
#                     # file_options={"contentType": "application/pdf"}
#                     file_options={"contentType": "application/pdf"}
#                 )

#                 document_data = {
#                     "file_name": file.filename,
#                     "doc_id_slug": to_ascii_id(file.filename),
#                     "storage_path": storage_path,
#                     "owner_id": user_id
#                 }
#                 supabase.table("documents").insert(document_data).execute()

#                 result = await pdf_processor.process_pdf(
#                     pdf_path=file_path_str,
#                     processing_mode=processing_mode,
#                     template_text=template_text,
#                     vector_db=vector_db_manager
#                 )
#                 results.append(result)

#             except Exception as e:
#                 print(f"Error processing {file.filename}: {e}")
#                 results.append({
#                     "doc_id": os.path.basename(file_path_str).split('.')[0],
#                     "status": "error", "error": str(e)
#                 })

#         return {
#             "message": "Files processed successfully",
#             "results": results
#         }
#     finally:
#         # supabase.auth.sign_out()
#         cleanup_temp_dir(temp_dir)

# โค้ดใหม่
@app.post("/upload-pdfs")
async def upload_and_process_pdfs_with_auth(
    current_user=Depends(get_current_user),
    authorization: Optional[str] = Header(None),
    files: List[UploadFile] = File(...),
    processing_mode: int = Form(1),
    use_template: bool = Form(False),
    template_file: Optional[UploadFile] = File(None)
):

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split(" ")[1]
    """
    รับไฟล์, ตรวจสอบสิทธิ์, บันทึกลง Supabase
    """

    # current_user = await get_current_user(authorization)
    user_id = current_user.id
    bucket_name = "assignments"  # <-- ชื่อ Bucket บน Supabase
    # token = authorization.split(" ")[1]

    if not pdf_processor or not embedding_manager or not vector_db_manager:
        raise HTTPException(status_code=503, detail="Service not ready.")
    if processing_mode not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid processing mode")
    validate_pdf_files(files)
    if use_template and not template_file:
        raise HTTPException(status_code=400, detail="Template file required")

    temp_dir = tempfile.mkdtemp(prefix="pdf_upload_")
    try:
        # supabase.auth.set_session(token)
        template_text = ""
        if use_template and template_file:
            template_path = os.path.join(temp_dir, template_file.filename)
            with open(template_path, "wb") as buffer:
                shutil.copyfileobj(template_file.file, buffer)
            template_text = pdf_processor.extract_template_text(template_path)

        results = []

        for file in files:
            file_path_str = os.path.join(temp_dir, file.filename)
            doc_id = to_ascii_id(file.filename)
            storage_path = f"{current_user.id}/{file.filename}"

            try:
                supabase_admin.from_("documents_duplicate").upsert({
                    "file_name": file.filename,
                    "doc_id": doc_id,
                    "storage_path": storage_path,
                    "user_id": current_user.id,
                    "status": "processing",
                    "processing_mode": processing_mode
                }).execute()

                # 2. PROCESS: ทำงานหนัก (อัปโหลดไป Storage และประมวลผล PDF)
                with open(file_path_str, "wb") as buffer:
                    file.file.seek(0)
                    shutil.copyfileobj(file.file, buffer)
                
                with open(file_path_str, "rb") as f:
                    file_content = f.read()
                
                print(f"Uploading '{file.filename}' to Supabase Storage")
                supabase_admin.storage.from_("assignments").upload(
                    path=storage_path,
                    file=file_content,
                    file_options={"contentType": "application/pdf"}
                )
                
                print(f"Processing PDF content for '{doc_id}'")
                # *** หมายเหตุ: ตรวจสอบชื่อพารามิเตอร์สุดท้ายให้ตรงกับฟังก์ชันของคุณ ***
                # อาจจะเป็น vector_db= หรือ vector_db_manager=
                metadata = await pdf_processor.process_pdf(
                    pdf_path=file_path_str,
                    doc_id=doc_id,
                    processing_mode=processing_mode,
                    template_text=template_text,
                    vector_db=vector_db_manager
                )

                # 3. UPDATE: นำผลลัพธ์มาอัปเดตแถวเดิมใน DB
                print(f"Success for '{doc_id}'. Updating status to 'success'")
                update_data = {
                    "status": "success",
                    "text_length": metadata.get("text_length"),
                    "image_count": metadata.get("image_count"),
                    "removed_text_length": metadata.get("removed_text_length")
                }
                supabase_admin.from_("documents_duplicate").update(update_data).eq("doc_id", doc_id).execute()
                
                results.append(metadata)

            except Exception as e:
                # 4. ERROR HANDLING: หากเกิดข้อผิดพลาด ให้อัปเดตสถานะใน DB
                error_message = str(e)
                print(f"❌ Error on '{doc_id}': {error_message}. Updating status to 'error'...")
                supabase_admin.from_("documents_duplicate").update({
                    "status": "error", 
                    "error": error_message
                }).eq("doc_id", doc_id).execute()

                results.append({ "doc_id": doc_id, "status": "error", "error": error_message })
        
        return { "message": "All files processed", "results": results }
    finally:
        # supabase.auth.sign_out()
        cleanup_temp_dir(temp_dir)


@app.get("/compare")
async def compare_documents():
    """
    Compare all processed documents for similarity

    Returns similarity scores between all document pairs
    """
    if not pdf_processor or not vector_db_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # Get all embeddings from vector database
        text_embeddings = await vector_db_manager.get_all_text_embeddings()
        image_embeddings, image_hashes = await vector_db_manager.get_all_image_embeddings()

        # Get document list
        doc_ids = list(pdf_processor.get_document_ids())

        if len(doc_ids) < 2:
            return {
                "message": "Need at least 2 documents to compare",
                "comparisons": [],
                "total_documents": len(doc_ids),
                "total_comparisons": 0
            }

        # Perform comparisons
        comparison_results = []
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                id1, id2 = doc_ids[i], doc_ids[j]

                # Calculate similarities
                result = pdf_processor.compare_documents(
                    id1, id2,
                    text_embeddings,
                    image_embeddings,
                    image_hashes
                )

                if result:
                    comparison_results.append(result)

        return {
            "comparisons": comparison_results,
            "total_documents": len(doc_ids),
            "total_comparisons": len(comparison_results)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Comparison error: {str(e)}")

#old def get_documents
# @app.get("/documents, response_model=List[DocumentResult]")
# async def get_documents(user=Depends(get_current_user)):
#     """Get list of all processed documents"""
#     if not pdf_processor:
#         raise HTTPException(status_code=503, detail="Service not ready")

#     doc_ids = list(pdf_processor.get_document_ids())

#     # Get document stats
#     document_details = []
#     for doc_id in doc_ids:
#         doc_info = pdf_processor.get_document_info(doc_id)
#         if doc_info:
#             document_details.append(doc_info)

#     return {
#         "documents": doc_ids,
#         "document_details": document_details,
#         "count": len(doc_ids)
#     }
#new def get_documents
@app.get("/documents", response_model=List[DocumentResult])
async def get_documents(user=Depends(get_current_user)):
    """ดึงรายการเอกสารทั้งหมดของผู้ใช้จากฐานข้อมูล Supabase โดยตรง"""
    try:
        # ใช้ supabase_admin เพื่อให้มีสิทธิ์อ่านข้อมูลจากฝั่ง server
        print(f"ดีงข้อมูลของ Authen : {user.id} ")
        
        # สมมติว่าตารางของคุณชื่อ 'documents'
        # และมีคอลัมน์ 'user_id' สำหรับระบุเจ้าของ
        query_res = supabase_admin.from_("documents_duplicate") \
                                  .select("doc_id, status, processing_mode, text_length, image_count, removed_text_length, error") \
                                  .eq("user_id", user.id) \
                                  .execute()

        if query_res.data:
            print(f"Found {len(query_res.data)} documents in Supabase.")
            return query_res.data
        else:
            print("No documents found for this user in Supabase.")
            return []

    except Exception as e:
        print(f"Error fetching documents from Supabase: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch documents from database.")


@app.delete("/documents")
async def clear_documents():
    """Clear all processed documents and embeddings"""
    if not pdf_processor or not vector_db_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # Clear from processor
        pdf_processor.clear_all_documents()

        # Clear from vector database
        await vector_db_manager.clear_all_indices()

        return {
            "message": "All documents cleared successfully",
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear error: {str(e)}")


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a specific document"""
    if not pdf_processor or not vector_db_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # Remove from processor
        if not pdf_processor.has_document(doc_id):
            raise HTTPException(status_code=404, detail="Document not found")

        pdf_processor.remove_document(doc_id)

        # Remove from vector database
        await vector_db_manager.delete_document_embeddings(doc_id)

        return {
            "message": f"Document {doc_id} deleted successfully",
            "doc_id": doc_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}")


@app.get("/stats")
async def get_stats():
    """ให้ข้อมูลสถิติเกี่ยวกับเอกสารที่ประมวลผลแล้วของผู้ใช้"""
    if not vector_db_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        text_stats = await vector_db_manager.get_text_index_stats()
        image_stats = await vector_db_manager.get_image_index_stats()

        return {
            "text_embeddings": text_stats,
            "image_embeddings": image_stats,
            "total_documents": len(pdf_processor.get_document_ids()) if pdf_processor else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")

# if __name__ == "__main__":
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,
#         log_level="info"
#     )