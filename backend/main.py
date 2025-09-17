from fastapi import FastAPI , File, UploadFile
from fastapi.responses import HTMLResponse
import uvicorn
from fastapi.responses import JSONResponse
import io
import fitz

app = FastAPI()

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import tempfile
import shutil
import uvicorn
from pathlib import Path

from pdf_processing import PDFProcessor
from embedding import EmbeddingManager
from vector_db import VectorDBManager
from utils import cleanup_temp_dir, validate_pdf_files

# Initialize FastAPI app
app = FastAPI(
    title="PDF Plagiarism Detection API", 
    version="1.0.0",
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

# Global managers
pdf_processor = None
embedding_manager = None
vector_db_manager = None

@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup"""
    global pdf_processor, embedding_manager, vector_db_manager
    
    print("🚀 Starting PDF Plagiarism Detection API...")
    
    try:
        # Initialize embedding manager
        print("📚 Loading embedding models...")
        embedding_manager = EmbeddingManager()
        await embedding_manager.initialize()
        
        # Initialize vector database
        print("🗄️ Connecting to vector database...")
        vector_db_manager = VectorDBManager()
        await vector_db_manager.initialize()
        
        # Initialize PDF processor
        print("📄 Setting up PDF processor...")
        pdf_processor = PDFProcessor(embedding_manager)
        
        print("✅ All components initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error during startup: {e}")
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

@app.post("/upload-pdfs")
async def upload_pdfs(
    files: List[UploadFile] = File(...),
    processing_mode: int = Form(1, description="1=Text only, 2=Images only, 3=Both"),
    use_template: bool = Form(False, description="Use template to remove common text"),
    template_file: Optional[UploadFile] = File(None, description="Template PDF file")
):
    """
    Upload and process PDF files
    
    - **processing_mode**: 1 = Text only, 2 = Images only, 3 = Both text and images
    - **use_template**: Whether to use a template file to remove common text
    - **template_file**: Template PDF file (required if use_template is True)
    """
    if not pdf_processor or not embedding_manager or not vector_db_manager:
        raise HTTPException(status_code=503, detail="Service not ready. Please wait for initialization.")
    
    # Validate processing mode
    if processing_mode not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Processing mode must be 1, 2, or 3")
    
    # Validate files
    validate_pdf_files(files)
    
    # Validate template requirement
    if use_template and not template_file:
        raise HTTPException(status_code=400, detail="Template file is required when use_template is True")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="pdf_upload_")
    
    try:
        # Save uploaded files
        pdf_paths = []
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            pdf_paths.append(file_path)
        
        # Process template if provided
        template_text = ""
        if use_template and template_file:
            template_path = os.path.join(temp_dir, template_file.filename)
            with open(template_path, "wb") as buffer:
                shutil.copyfileobj(template_file.file, buffer)
            template_text = pdf_processor.extract_template_text(template_path)
        
        # Process each PDF
        results = []
        for pdf_path in pdf_paths:
            try:
                result = await pdf_processor.process_pdf(
                    pdf_path=pdf_path,
                    processing_mode=processing_mode,
                    template_text=template_text if use_template else None,
                    vector_db=vector_db_manager
                )
                results.append(result)
                
            except Exception as e:
                print(f"Error processing {pdf_path}: {e}")
                results.append({
                    "doc_id": os.path.basename(pdf_path).split('.')[0],
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "message": "Files processed successfully",
            "processing_mode": processing_mode,
            "use_template": use_template,
            "total_files": len(files),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Clean up temporary directory
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
        raise HTTPException(status_code=500, detail=f"Comparison error: {str(e)}")

@app.get("/documents")
async def get_documents():
    """Get list of all processed documents"""
    if not pdf_processor:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    doc_ids = list(pdf_processor.get_document_ids())
    
    # Get document stats
    document_details = []
    for doc_id in doc_ids:
        doc_info = pdf_processor.get_document_info(doc_id)
        if doc_info:
            document_details.append(doc_info)
    
    return {
        "documents": doc_ids,
        "document_details": document_details,
        "count": len(doc_ids)
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
    """Get system statistics"""
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )