"""
Script test: Nhập câu hỏi từ console và in ra kết quả từ RAG pipeline
"""

import json
from app.models.schemas import QueryRequest
from app.rag.pipeline import get_rag_pipeline

def main():
    print("\n" + "="*80)
    print("RAG QUERY TEST - HỆTHỐNG PHÁP LUẬT VIỆT NAM")
    print("="*80)
    print("Nhập 'quit' hoặc 'exit' để thoát\n")
    
    # Khởi tạo pipeline
    print("[*] Khởi tạo RAG pipeline...")
    pipeline = get_rag_pipeline()
    
    if pipeline is None:
        print("❌ LỖI: Không thể khởi tạo RAG pipeline!")
        return
    
    print("✅ RAG pipeline sẵn sàng!\n")
    
    while True:
        # Nhập câu hỏi
        print("-" * 80)
        query = input("❓ Nhập câu hỏi (hoặc 'quit' để thoát): ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Tạm biệt!")
            break
        
        if not query:
            print("⚠️ Vui lòng nhập một câu hỏi!")
            continue
        
        # Tạo request
        request = QueryRequest(query=query, top_k=5)
        
        # Xử lý query
        print("\n[⏳] Đang xử lý query...")
        try:
            response = pipeline.process_query(request)
            
            # In kết quả
            print("\n" + "="*80)
            print("📝 KẾT QUẢ")
            print("="*80)
            
            print(f"\n❓ Câu hỏi: {response.query}")
            print(f"\n⏱️ Thời gian xử lý: {response.processing_time:.2f}s")
            print(f"🤖 Model sử dụng: {response.model_used}")
            
            print(f"\n{'='*80}")
            print("💬 CÂU TRẢ LỜI:")
            print(f"{'='*80}")
            print(f"\n{response.answer}\n")
            
            print(f"{'='*80}")
            print(f"📚 TÀI LIỆU LIÊN QUAN ({len(response.sources)} sources):")
            print(f"{'='*80}\n")
            
            for idx, source in enumerate(response.sources, 1):
                print(f"[{idx}] {source.title}")
                print(f"    Điểm liên quan: {source.relevance_score:.2%}")
                if source.metadata:
                    meta = source.metadata
                    if 'article_num' in meta:
                        print(f"    Điều: {meta.get('article_num', 'N/A')}")
                    if 'chapter' in meta:
                        print(f"    Chương: {meta.get('chapter', 'N/A')}")
                print(f"    Nội dung: {source.content[:150]}...")
                print()
            
            # Lưu response vào JSON (tùy chọn)
            json_file = f"query_response_{response.processing_time:.0f}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "query": response.query,
                    "answer": response.answer,
                    "processing_time": response.processing_time,
                    "model_used": response.model_used,
                    "sources": [
                        {
                            "title": s.title,
                            "relevance_score": s.relevance_score,
                            "metadata": s.metadata,
                            "content": s.content[:200]
                        }
                        for s in response.sources
                    ]
                }, f, ensure_ascii=False, indent=2)
            print(f"✅ Kết quả đã lưu: {json_file}\n")
            
        except Exception as e:
            print(f"\n❌ LỖI: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
