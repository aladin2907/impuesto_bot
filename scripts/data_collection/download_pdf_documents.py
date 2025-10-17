#!/usr/bin/env python3
"""
Скрипт для скачивания PDF документов (законы, регламенты)
"""

import json
import requests
import hashlib
from datetime import datetime
from typing import List, Dict
from pathlib import Path


class PDFDownloader:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # Список документов для скачивания
        self.documents = [
            {
                "document_title": "Ley 35/2006 IRPF - Impuesto sobre la Renta de las Personas Físicas",
                "document_type": "law",
                "document_number": "Ley 35/2006",
                "source_url": "https://www.boe.es/buscar/pdf/2006/BOE-A-2006-20764-consolidado.pdf",
                "categories": ["irpf", "renta", "autonomos"],
                "description": "Ley del Impuesto sobre la Renta de las Personas Físicas",
                "region": "national",
                "language": "es"
            },
            {
                "document_title": "Ley 37/1992 IVA - Impuesto sobre el Valor Añadido",
                "document_type": "law",
                "document_number": "Ley 37/1992",
                "source_url": "https://www.boe.es/buscar/pdf/1992/BOE-A-1992-28740-consolidado.pdf",
                "categories": ["iva", "impuesto_indirecto"],
                "description": "Ley del Impuesto sobre el Valor Añadido",
                "region": "national",
                "language": "es"
            },
            {
                "document_title": "Real Decreto 439/2007 Reglamento IRPF",
                "document_type": "regulation",
                "document_number": "RD 439/2007",
                "source_url": "https://www.boe.es/buscar/pdf/2007/BOE-A-2007-7648-consolidado.pdf",
                "categories": ["irpf", "reglamento"],
                "description": "Reglamento del Impuesto sobre la Renta de las Personas Físicas",
                "region": "national",
                "language": "es"
            },
            {
                "document_title": "Ley 27/2014 Impuesto sobre Sociedades",
                "document_type": "law",
                "document_number": "Ley 27/2014",
                "source_url": "https://www.boe.es/buscar/pdf/2014/BOE-A-2014-12328-consolidado.pdf",
                "categories": ["sociedades", "empresas"],
                "description": "Ley del Impuesto sobre Sociedades",
                "region": "national",
                "language": "es"
            }
        ]
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Вычисляет SHA256 hash файла"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def download_pdf(self, url: str, output_path: str) -> Dict:
        """Скачивает PDF файл"""
        try:
            print(f"📥 Скачиваем: {output_path}...")
            
            response = requests.get(url, headers=self.headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Создаём директорию если не существует
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Скачиваем файл
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Получаем размер файла
            file_size = Path(output_path).stat().st_size
            
            # Вычисляем hash
            file_hash = self.calculate_file_hash(output_path)
            
            print(f"✅ Скачан: {file_size:,} байт (hash: {file_hash[:16]}...)")
            
            return {
                "success": True,
                "file_path": output_path,
                "file_size_bytes": file_size,
                "file_hash": file_hash,
                "downloaded_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def download_all_documents(self, output_dir: str = "data/pdf_documents"):
        """Скачивает все документы"""
        print(f"📚 Скачиваем {len(self.documents)} документов...")
        print(f"{'='*60}\n")
        
        results = []
        
        for doc in self.documents:
            print(f"📄 {doc['document_title']}")
            print(f"   Тип: {doc['document_type']}")
            print(f"   Номер: {doc['document_number']}")
            
            # Формируем имя файла
            filename = f"{doc['document_number'].replace('/', '_').replace(' ', '_')}.pdf"
            output_path = f"{output_dir}/{filename}"
            
            # Скачиваем
            download_result = self.download_pdf(doc['source_url'], output_path)
            
            # Объединяем результат с метаданными
            result = {**doc, **download_result}
            results.append(result)
            
            print()
        
        return results
    
    def save_metadata(self, results: List[Dict], output_file: str):
        """Сохраняет метаданные документов"""
        data = {
            "collected_at": datetime.now().isoformat(),
            "total_documents": len(results),
            "successful_downloads": sum(1 for r in results if r.get('success')),
            "failed_downloads": sum(1 for r in results if not r.get('success')),
            "documents": results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Метаданные сохранены в {output_file}")
    
    def analyze_documents(self, results: List[Dict]):
        """Анализирует скачанные документы"""
        print(f"\n{'='*60}")
        print("АНАЛИЗ PDF ДОКУМЕНТОВ")
        print(f"{'='*60}")
        
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        print(f"\n📊 Статистика:")
        print(f"  Всего документов: {len(results)}")
        print(f"  Успешно скачано: {len(successful)}")
        print(f"  Ошибок: {len(failed)}")
        
        if successful:
            total_size = sum(r.get('file_size_bytes', 0) for r in successful)
            print(f"  Общий размер: {total_size:,} байт ({total_size / 1024 / 1024:.2f} MB)")
        
        # Типы документов
        doc_types = {}
        for doc in results:
            doc_type = doc.get('document_type', 'unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        print(f"\n📋 Типы документов:")
        for doc_type, count in sorted(doc_types.items()):
            print(f"  - {doc_type}: {count}")
        
        # Категории
        all_categories = set()
        for doc in results:
            all_categories.update(doc.get('categories', []))
        
        print(f"\n🏷️ Категории ({len(all_categories)}):")
        for category in sorted(all_categories):
            count = sum(1 for d in results if category in d.get('categories', []))
            print(f"  - {category}: {count} документов")
        
        # Детали успешных загрузок
        if successful:
            print(f"\n📄 Успешно скачанные документы:")
            for doc in successful:
                print(f"\n  • {doc['document_title']}")
                print(f"    Файл: {doc['file_path']}")
                print(f"    Размер: {doc['file_size_bytes']:,} байт")
                print(f"    Hash: {doc['file_hash'][:32]}...")
        
        # Ошибки
        if failed:
            print(f"\n❌ Ошибки при скачивании:")
            for doc in failed:
                print(f"\n  • {doc['document_title']}")
                print(f"    Ошибка: {doc.get('error', 'Unknown')}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Скачивание PDF документов')
    parser.add_argument('--output-dir', default='data/pdf_documents', help='Директория для сохранения PDF')
    parser.add_argument('--metadata', default='data/pdf_metadata.json', help='Файл для метаданных')
    
    args = parser.parse_args()
    
    downloader = PDFDownloader()
    
    # Скачиваем документы
    results = downloader.download_all_documents(args.output_dir)
    
    # Анализируем
    downloader.analyze_documents(results)
    
    # Сохраняем метаданные
    import os
    os.makedirs(os.path.dirname(args.metadata), exist_ok=True)
    downloader.save_metadata(results, args.metadata)


if __name__ == "__main__":
    main()

