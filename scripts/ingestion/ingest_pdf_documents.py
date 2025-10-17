"""
Ingest PDF documents (Tax Code, Tax Calendar, etc.)
Usage: python scripts/ingestion/ingest_pdf_documents.py <path_to_pdf> [--url <source_url>]
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from langchain_community.document_loaders import PyPDFLoader
from scripts.ingestion.base_ingestor import BaseIngestor


class PDFIngestor(BaseIngestor):
    """Ingestor for PDF documents"""
    
    def __init__(self):
        super().__init__(
            chunk_size=1000,
            chunk_overlap=200,
            document_type="tax_code"  # Can be: tax_code, tax_calendar, regulation
        )
    
    def load_pdf(self, pdf_path: str):
        """
        Load PDF document using LangChain
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of Document objects
        """
        try:
            print(f"Loading PDF: {pdf_path}")
            
            if not os.path.exists(pdf_path):
                print(f"❌ File not found: {pdf_path}")
                return None
            
            # Use PyPDFLoader from LangChain
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            
            print(f"✅ Loaded {len(documents)} pages from PDF")
            return documents
            
        except Exception as e:
            print(f"❌ Failed to load PDF: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def process_pdf(
        self,
        pdf_path: str,
        source_url: str = None,
        document_type: str = "tax_code"
    ) -> bool:
        """
        Complete pipeline: load PDF -> split -> embed -> index
        
        Args:
            pdf_path: Path to PDF file
            source_url: Original URL of the document
            document_type: Type of document (tax_code, tax_calendar, etc.)
            
        Returns:
            True if successful
        """
        self.document_type = document_type
        
        # Step 1: Initialize services
        if not self.initialize():
            return False
        
        # Step 2: Load PDF
        documents = self.load_pdf(pdf_path)
        if not documents:
            self.cleanup()
            return False
        
        # Step 3: Save metadata to Supabase
        file_name = os.path.basename(pdf_path)
        doc_id = self.save_document_metadata(
            file_name=file_name,
            source_url=source_url,
            status="processing"
        )
        
        # Step 4: Add metadata to chunks
        metadata = {
            "source": file_name,
            "document_type": document_type,
            "document_id": str(doc_id) if doc_id else None
        }
        
        for doc in documents:
            doc.metadata.update(metadata)
        
        # Step 5: Ingest into Elasticsearch
        success = self.ingest_documents(documents)
        
        # Step 6: Update status in Supabase
        if success and doc_id:
            try:
                cursor = supabase_service.connection.cursor()
                cursor.execute("""
                    UPDATE documents
                    SET status = 'completed', last_processed_at = NOW()
                    WHERE id = %s
                """, (doc_id,))
                supabase_service.connection.commit()
                print("✅ Document status updated to 'completed'")
            except Exception as e:
                print(f"⚠️  Failed to update status: {e}")
        
        # Step 7: Cleanup
        self.cleanup()
        
        if success:
            print("\n" + "="*60)
            print("✅ PDF INGESTION COMPLETED SUCCESSFULLY!")
            print("="*60)
            print(f"📄 File: {file_name}")
            print(f"📊 Pages: {len(documents)}")
            print(f"🔍 Indexed in Elasticsearch: {settings.ELASTIC_INDEX_NAME}")
            print(f"💾 Metadata saved in Supabase")
            print("="*60)
        
        return success


def main():
    """Main function to run from command line"""
    parser = argparse.ArgumentParser(
        description="Ingest PDF documents into TuExpertoFiscal NAIL knowledge base"
    )
    parser.add_argument(
        "pdf_path",
        help="Path to the PDF file to ingest"
    )
    parser.add_argument(
        "--url",
        help="Source URL of the document (optional)",
        default=None
    )
    parser.add_argument(
        "--type",
        help="Document type (tax_code, tax_calendar, regulation)",
        default="tax_code",
        choices=["tax_code", "tax_calendar", "regulation", "guide"]
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("TuExpertoFiscal NAIL - PDF Ingestion")
    print("="*60)
    print(f"PDF: {args.pdf_path}")
    print(f"Type: {args.type}")
    print(f"Source URL: {args.url or 'Not provided'}")
    print("="*60)
    print()
    
    # Create ingestor and process
    ingestor = PDFIngestor()
    success = ingestor.process_pdf(
        pdf_path=args.pdf_path,
        source_url=args.url,
        document_type=args.type
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
