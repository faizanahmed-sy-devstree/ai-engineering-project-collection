# app/projects/p03_summarizer/router.py
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from pypdf import PdfReader
from app.core.gemini import get_client

router = APIRouter()
client = get_client()

def extract_text(file_name: str, content: bytes) -> str:
    """Helper function to extract text from .txt or .pdf files"""
    if file_name.endswith('.txt'):
        return content.decode('utf-8')
    elif file_name.endswith('.pdf'):
        # Use io.BytesIO to read the PDF from memory instead of saving to disk
        pdf_file = io.BytesIO(content)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    else:
        raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported")

def chunk_text(text: str, chunk_size: int = 6000) -> list[str]:
    """
    Splits text into smaller chunks. 
    A rough estimate is 4 characters = 1 token. 
    6000 chars is roughly 1500 tokens.
    """
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

@router.post("/summarize")
async def summarize_document(file: UploadFile = File(...)):
    # 1. Read the uploaded file into memory
    content = await file.read()
    
    # 2. Extract text based on file type
    full_text = extract_text(file.filename, content)
    
    # 3. Chunk the document
    chunks = chunk_text(full_text)
    
    # ==========================================
    # 4. MAP STEP: Summarize each chunk individually
    # ==========================================
    chunk_summaries =[]
    for i, chunk in enumerate(chunks):
        map_prompt = f"Summarize the following section of a document. Keep it concise:\n\n{chunk}"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=map_prompt
        )
        chunk_summaries.append(response.text)
        
    # ==========================================
    # 5. REDUCE STEP: Combine and summarize the summaries
    # ==========================================
    if len(chunk_summaries) > 1:
        combined_summaries = "\n\n---\n\n".join(chunk_summaries)
        reduce_prompt = f"""
        Here are summaries of different sections of a single document. 
        Combine them into one cohesive, comprehensive final summary:
        
        {combined_summaries}
        """
        
        final_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=reduce_prompt
        )
        final_summary = final_response.text
    else:
        # If the document was small enough to fit in one chunk, no need to reduce!
        final_summary = chunk_summaries[0]
        
    return {
        "filename": file.filename,
        "total_chunks_processed": len(chunks),
        "final_summary": final_summary
    }