from supabase import create_client, Client
from utils import to_ascii_id
from supabase_client import supabase
from auth import get_current_user
from auth import router as auth_router
from utils import cleanup_temp_dir, validate_pdf_files
from vector_db import VectorDBManager
from embedding import EmbeddingManager
from pdf_processing import PDFProcessor
from clustering_utils import cluster_by_threshold
from pydantic import BaseModel, Field
from typing import List, Optional
from clustering_utils import cluster_by_threshold
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

class Pair(BaseModel):
    doc_1: str
    doc_2: str
    final_score: Optional[float] = None
    combined_score: Optional[float] = None

class ClusterReq(BaseModel):
    threshold: float = Field(0.8, ge=0.0, le=1.0)
    pairs: List[Pair]


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
    batch_id:str = Form(...), # เพิ่ม batch_id สำหรับติดตามกลุ่มการอัปโหลด
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
                    "processing_mode": processing_mode,
                    "batch_id": batch_id  # บันทึก batch_id ลงในฐานข้อมูล
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
                    vector_db=vector_db_manager,
                    user_id=current_user.id,
                    batch_id=batch_id
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

#old compare_documents
# @app.get("/compare")
# async def compare_documents():
#     """
#     Compare all processed documents for similarity

#     Returns similarity scores between all document pairs
#     """
#     if not pdf_processor or not vector_db_manager:
#         raise HTTPException(status_code=503, detail="Service not ready")

#     try:
#         # Get all embeddings from vector database
#         text_embeddings = await vector_db_manager.get_all_text_embeddings()
#         image_embeddings, image_hashes = await vector_db_manager.get_all_image_embeddings()

#         # Get document list
#         doc_ids = list(pdf_processor.get_document_ids())

#         if len(doc_ids) < 2:
#             return {
#                 "message": "Need at least 2 documents to compare",
#                 "comparisons": [],
#                 "total_documents": len(doc_ids),
#                 "total_comparisons": 0
#             }

#         # Perform comparisons
#         comparison_results = []
#         for i in range(len(doc_ids)):
#             for j in range(i + 1, len(doc_ids)):
#                 id1, id2 = doc_ids[i], doc_ids[j]

#                 # Calculate similarities
#                 result = pdf_processor.compare_documents(
#                     id1, id2,
#                     text_embeddings,
#                     image_embeddings,
#                     image_hashes
#                 )

#                 if result:
#                     comparison_results.append(result)

#         return {
#             "comparisons": comparison_results,
#             "total_documents": len(doc_ids),
#             "total_comparisons": len(comparison_results)
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"Comparison error: {str(e)}")
        
        
#new compare_documents
# ในไฟล์ main.py

# ใน main.py - แทนที่ฟังก์ชัน compare_documents เดิม

@app.get("/compare", summary="Compare documents within a specific batch")
async def compare_documents_in_batch(
    batch_id: str,
    current_user=Depends(get_current_user)
):
    """
    Compares all documents for the authenticated user within a specific upload batch.
    """
    if not pdf_processor or not vector_db_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    user_id = current_user.id
    print(f"\n========== COMPARISON REQUEST ==========")
    print(f"User ID: {user_id}")
    print(f"Batch ID: {batch_id}")

    try:
        # 1. ดึงข้อมูลจาก Pinecone
        text_embeddings_raw, image_embeddings_raw = await vector_db_manager.retrieve_embeddings_for_batch(
            user_id,
            batch_id
        )

        print(f"📊 Retrieved: {len(text_embeddings_raw)} text, {len(image_embeddings_raw)} image embeddings")

        if not text_embeddings_raw and not image_embeddings_raw:
            print(f"⚠️ No embeddings found for batch {batch_id}")
            return []

        # 2. แยก doc_ids
        doc_ids_set = set()
        for key in text_embeddings_raw.keys():
            if key.startswith("text_"):
                doc_id = key[5:]  # ตัด "text_" ออก
                doc_ids_set.add(doc_id)

        for key in image_embeddings_raw.keys():
            if key.startswith("image_"):
                parts = key.split("_")
                if len(parts) >= 3:
                    doc_id = "_".join(parts[1:-1])
                    doc_ids_set.add(doc_id)

        all_doc_ids = sorted(list(doc_ids_set))
        print(f"📋 Document IDs: {all_doc_ids}")

        if len(all_doc_ids) < 2:
            print(f"⚠️ Need at least 2 documents, found {len(all_doc_ids)}")
            return []

        # 3. ดึงข้อมูลเอกสารจาก Supabase เพื่อเอา text
        print("\n📚 Loading document texts from Supabase...")
        doc_texts = {}
        doc_metadata = {}
        
        for doc_id in all_doc_ids:
            try:
                # Query document info
                print(f"DEBUG: Querying Supabase for doc_id='{doc_id}' and user_id='{user_id}'")
                result = supabase_admin.from_("documents_duplicate") \
                    .select("*") \
                    .eq("doc_id", doc_id) \
                    .eq("user_id", user_id) \
                    .eq("batch_id", batch_id) \
                    .order("created_at", desc=True) \
                    .limit(1) \
                    .execute()
                
                if result.data and len(result.data) > 0:
                    doc_info = result.data[0]
                    storage_path = doc_info.get("storage_path")
                    processing_mode = doc_info.get("processing_mode", 3)
                    
                    need_text = processing_mode in [1, 3]
                    
                    # Download PDF from storage และ extract text
                    if need_text and storage_path:
                        try:
                            # Download file
                            file_data = supabase_admin.storage.from_("assignments").download(storage_path)
                            
                            # Save to temp file
                            import tempfile
                            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                                tmp.write(file_data)
                                tmp_path = tmp.name
                            
                            # Extract text
                            extracted_text = pdf_processor.extract_text_from_pdf(tmp_path)
                            doc_texts[doc_id] = extracted_text
                            
                            # Clean up temp file
                            import os
                            os.unlink(tmp_path)
                            
                            print(f"  ✓ {doc_id}: {len(extracted_text)} characters (Mode {processing_mode})")
                            
                        except Exception as e:
                            print(f"  ⚠️ Could not extract text for {doc_id}: {e}")
                            doc_texts[doc_id] = ""
                    else:
                        doc_texts[doc_id] = ""
                        print(f"  {doc_id}: Skipping text extraction (Mode {processing_mode} - Image Only)")
                    
                    # Store metadata
                    doc_metadata[doc_id] = {
                        "processing_mode": processing_mode,
                        "text_length": len(doc_texts.get(doc_id, "")),
                        "has_template": False
                    }
                    
            except Exception as e:
                print(f"  ⚠️ Error loading {doc_id}: {e}")
                doc_texts[doc_id] = ""
                doc_metadata[doc_id] = {"processing_mode": 1}

        # 4. อัปเดต pdf_processor ด้วยข้อมูลที่โหลดมา
        for doc_id, text in doc_texts.items():
            pdf_processor.raw_texts[doc_id] = text
            if doc_id in doc_metadata:
                pdf_processor.document_metadata[doc_id] = doc_metadata[doc_id]

        # 5. เตรียมข้อมูลสำหรับการเปรียบเทียบ
        text_embeddings_for_compare = text_embeddings_raw
        
        # จัดกลุ่ม image embeddings ตาม doc_id
        image_embeddings_for_compare = {}
        image_hashes_for_compare = {}
        
        for vector_id, embedding in image_embeddings_raw.items():
            if vector_id.startswith("image_"):
                # parts = vector_id.split("_")
                remaining = vector_id[6:]  
                parts = remaining.split("_")
                if len(parts) >= 2:
                    doc_id = "_".join(parts[:-1])
                    
                    image_embeddings_for_compare[vector_id] = embedding
                    
                    # if doc_id not in image_embeddings_for_compare:
                    #     image_embeddings_for_compare[doc_id] = []
                    #     image_hashes_for_compare[doc_id] = []
                    
                    # image_embeddings_for_compare[doc_id].append(embedding)
                    
                    # ดึง phash
                    try:
                        result = vector_db_manager.image_index.fetch(ids=[vector_id])
                        if result.vectors and vector_id in result.vectors:
                            phash = result.vectors[vector_id].metadata.get("phash", "")
                            image_hashes_for_compare[vector_id] = phash
                        else:
                            image_hashes_for_compare[vector_id] = ""
                    except Exception as e:
                        print(f"  ⚠️ Could not fetch phash for {vector_id}: {e}")
                        image_hashes_for_compare[vector_id] = ""

        print(f"\nReady to compare:")
        print(f"  Text embeddings: {list(text_embeddings_for_compare.keys())}")
        print(f"  Doc texts loaded: {list(doc_texts.keys())}")
        print(f"  Image embeddings: {len(image_embeddings_for_compare)} vectors")
        print(f"  Image vector IDs sample: {list(image_embeddings_for_compare.keys())[:3]}")

        # 6. เปรียบเทียบทุกคู่
        comparison_results = []
        total_pairs = (len(all_doc_ids) * (len(all_doc_ids) - 1)) // 2
        print(f"\n🔄 Starting {total_pairs} comparisons...")
        
        for i in range(len(all_doc_ids)):
            for j in range(i + 1, len(all_doc_ids)):
                id1, id2 = all_doc_ids[i], all_doc_ids[j]
                
                print(f"\n  Comparing: {id1} vs {id2}")
                
                result = pdf_processor.compare_documents(
                    id1,
                    id2,
                    text_embeddings_for_compare,
                    image_embeddings_for_compare,
                    image_hashes_for_compare
                )
                
                if result:
                    print(f"    ✓ Combined score: {result['combined_score']:.4f}")
                    comparison_results.append(result)
                else:
                    print(f"    ⚠️ Comparison returned None")

        # 7. เรียงลำดับผลลัพธ์
        sorted_results = sorted(
            comparison_results,
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        print(f"\n========== COMPARISON COMPLETE ==========")
        print(f"Total comparisons: {len(sorted_results)}")
        if sorted_results:
            print(f"Highest score: {sorted_results[0]['combined_score']:.4f}")
            print(f"Lowest score: {sorted_results[-1]['combined_score']:.4f}")
        
        return sorted_results

    except Exception as e:
        print(f"❌ Error during comparison: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Comparison error: {str(e)}"
        )  
        
        

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
async def get_documents(user=Depends(get_current_user), batch_id: Optional[str] = None):
    """ดึงรายการเอกสารทั้งหมดของผู้ใช้จากฐานข้อมูล Supabase โดยตรง"""
    try:
        # ใช้ supabase_admin เพื่อให้มีสิทธิ์อ่านข้อมูลจากฝั่ง server
        print(f"ดีงข้อมูลของ Authen : {user.id} ")
        
        # สมมติว่าตารางของคุณชื่อ 'documents'
        # และมีคอลัมน์ 'user_id' สำหรับระบุเจ้าของ
        query_res = supabase_admin.from_("documents_duplicate") \
                                  .select("doc_id, status, processing_mode, text_length, image_count, removed_text_length, error") \
                                  .eq("user_id", user.id) \
                                  .eq("batch_id",batch_id) \
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


@app.post("/cluster")
async def cluster_documents(payload: ClusterReq, current_user=Depends(get_current_user)):
    """
    รับผล pair จาก /compare แล้วจัดกลุ่มตาม threshold
    pairs สามารถส่ง final_score หรือ combined_score มาก็ได้ (อย่างใดอย่างหนึ่ง)
    """
    import pandas as pd

    rows = []
    for p in payload.pairs:
        # เลือกคะแนนจาก final_score ถ้ามี ไม่งั้น fallback เป็น combined_score
        score = p.final_score if p.final_score is not None else (p.combined_score or 0.0)
        rows.append({"doc_1": p.doc_1, "doc_2": p.doc_2, "final_score": float(score)})

    df = pd.DataFrame(rows, columns=["doc_1", "doc_2", "final_score"])
    clusters = cluster_by_threshold(df, payload.threshold)
    return {
        "threshold": payload.threshold,
        "cluster_count": len(clusters),
        "clusters": clusters
    }




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

# เพิ่ม endpoint นี้ใน main.py เพื่อ debug

@app.get("/debug/simple/{batch_id}")
async def simple_debug(batch_id: str):
    """Simple debug endpoint - ดูว่ามีข้อมูลอะไรใน Pinecone บ้าง"""
    if not vector_db_manager or not vector_db_manager.is_connected():
        return {"error": "Vector DB not connected"}
    
    try:
        print(f"\n========== SIMPLE DEBUG: {batch_id} ==========")
        
        result = {
            "batch_id": batch_id,
            "text_vectors": [],
            "image_vectors": [],
            "errors": []
        }
        
        # 1. ดู text index
        try:
            print("Querying text index...")
            text_response = vector_db_manager.text_index.query(
                vector=[0.0] * 768,  # TEXT_DIMENSION
                top_k=100,
                include_metadata=True
            )
            
            print(f"Found {len(text_response.matches)} text vectors")
            
            for match in text_response.matches:
                vec_info = {
                    "id": match.id,
                    "metadata": match.metadata if match.metadata else {}
                }
                result["text_vectors"].append(vec_info)
                
                # แสดงใน console
                print(f"  Text Vector: {match.id}")
                if match.metadata:
                    print(f"    Metadata: {match.metadata}")
                    
        except Exception as e:
            error_msg = f"Text index error: {str(e)}"
            print(f"❌ {error_msg}")
            result["errors"].append(error_msg)
        
        # 2. ดู image index
        try:
            print("\nQuerying image index...")
            image_response = vector_db_manager.image_index.query(
                vector=[0.0] * 768,  # IMAGE_DIMENSION
                top_k=100,
                include_metadata=True
            )
            
            print(f"Found {len(image_response.matches)} image vectors")
            
            for match in image_response.matches:
                vec_info = {
                    "id": match.id,
                    "metadata": match.metadata if match.metadata else {}
                }
                result["image_vectors"].append(vec_info)
                
                # แสดงใน console
                print(f"  Image Vector: {match.id}")
                if match.metadata:
                    print(f"    Metadata: {match.metadata}")
                    
        except Exception as e:
            error_msg = f"Image index error: {str(e)}"
            print(f"❌ {error_msg}")
            result["errors"].append(error_msg)
        
        # 3. Filter เฉพาะ batch นี้
        result["batch_text_vectors"] = [
            v for v in result["text_vectors"]
            if v.get("metadata", {}).get("batch_id") == batch_id
        ]
        
        result["batch_image_vectors"] = [
            v for v in result["image_vectors"]
            if v.get("metadata", {}).get("batch_id") == batch_id
        ]
        
        print(f"\n========== SUMMARY ==========")
        print(f"Total text vectors: {len(result['text_vectors'])}")
        print(f"Total image vectors: {len(result['image_vectors'])}")
        print(f"Batch text vectors: {len(result['batch_text_vectors'])}")
        print(f"Batch image vectors: {len(result['batch_image_vectors'])}")
        
        return result
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "traceback": traceback.format_exc()}


@app.get("/debug/test-filter/{batch_id}")
async def test_filter(batch_id: str):
    """ทดสอบว่า filter ใน Pinecone ทำงานหรือไม่"""
    if not vector_db_manager or not vector_db_manager.is_connected():
        return {"error": "Vector DB not connected"}
    
    try:
        print(f"\n========== TESTING FILTER: {batch_id} ==========")
        
        # ทดสอบ filter แบบต่างๆ
        test_results = {}
        
        # Test 1: ไม่ใช้ filter
        try:
            response = vector_db_manager.text_index.query(
                vector=[0.0] * 768,
                top_k=10,
                include_metadata=True
            )
            test_results["no_filter"] = {
                "count": len(response.matches),
                "vectors": [{"id": m.id, "metadata": m.metadata} for m in response.matches]
            }
            print(f"No filter: {len(response.matches)} results")
        except Exception as e:
            test_results["no_filter"] = {"error": str(e)}
        
        # Test 2: Filter แบบ $eq
        try:
            response = vector_db_manager.text_index.query(
                vector=[0.0] * 768,
                top_k=10,
                filter={"batch_id": {"$eq": batch_id}},
                include_metadata=True
            )
            test_results["filter_eq"] = {
                "count": len(response.matches),
                "vectors": [{"id": m.id, "metadata": m.metadata} for m in response.matches]
            }
            print(f"Filter $eq: {len(response.matches)} results")
        except Exception as e:
            test_results["filter_eq"] = {"error": str(e)}
        
        # Test 3: Filter แบบง่าย
        try:
            response = vector_db_manager.text_index.query(
                vector=[0.0] * 768,
                top_k=10,
                filter={"batch_id": batch_id},
                include_metadata=True
            )
            test_results["filter_simple"] = {
                "count": len(response.matches),
                "vectors": [{"id": m.id, "metadata": m.metadata} for m in response.matches]
            }
            print(f"Filter simple: {len(response.matches)} results")
        except Exception as e:
            test_results["filter_simple"] = {"error": str(e)}
        
        return {
            "batch_id": batch_id,
            "tests": test_results
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}