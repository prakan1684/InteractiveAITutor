# backend/tests/test_course_rag.py

import sys
import os
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from app.services.course_rag_service import CourseRAGService

def test_course_rag():
    print("🎓 Testing CourseRAGService...")
    
    # Initialize service
    print("\n1️⃣ Initializing CourseRAGService...")
    service = CourseRAGService()
    print("✅ Service initialized")
    
    # Test paragraph splitting
    print("\n2️⃣ Testing paragraph splitting...")
    test_text = """
    The quadratic formula is given by:
    
    $$x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$$
    
    This formula works for any quadratic equation of the form $ax^2 + bx + c = 0$.
    
    For example, if we have $x^2 + 5x + 6 = 0$, then a=1, b=5, c=6.
    """
    
    paragraphs = service._split_into_paragraphs(test_text)
    print(f"✅ Split into {len(paragraphs)} paragraphs")
    for i, para in enumerate(paragraphs, 1):
        print(f"\n  Paragraph {i}:")
        print(f"  {para[:100]}...")
    
    # Test chunking
    print("\n3️⃣ Testing chunking...")
    page_data = {
        "page": 1,
        "text": test_text,
        "has_tables": False
    }
    chunks = service._chunk_page(page_data, "test.pdf")
    print(f"✅ Created {len(chunks)} chunks")
    for chunk in chunks:
        print(f"\n  Chunk {chunk['chunk_index']}:")
        print(f"  Length: {chunk['char_count']} chars")
        print(f"  Content: {chunk['content'][:80]}...")
    
    print("\n✅ All basic tests passed!")
    print("\n⚠️  To test PDF upload, you need a sample PDF file.")
    print("   Place a PDF in backend/tests/sample.pdf and uncomment the upload test below.")
    
    
    print("\n4️⃣ Testing PDF upload...")
    result = service.upload_pdf("tests/sample.pdf")
    print(f"✅ Upload result: {result}")
    
    print("\n5️⃣ Testing search...")
    results = service.search_materials("polynomials", top_k=3)
    print(f"✅ Found {len(results)} results")
    for i, result in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"  Source: {result['source_file']} (page {result['page_number']})")
        print(f"  Score: {result['score']:.4f}")
        print(f"  Content: {result['content'][:100]}...")

if __name__ == "__main__":
    test_course_rag()