#!/usr/bin/env python3
"""
Скрипт для скачивания испанских налоговых документов
"""

import os
import sys
import requests
from pathlib import Path
from urllib.parse import urlparse
import time

# Добавляем корневую папку в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import Settings


class TaxDocumentDownloader:
    """Класс для скачивания налоговых документов"""
    
    def __init__(self):
        self.settings = Settings()
        self.download_dir = Path("data/tax_documents")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Список документов для скачивания
        self.documents = [
            {
                "name": "LGT_General_Tax_Law",
                "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2003-23186",
                "type": "html",
                "description": "Ley General Tributaria (LGT) - General Tax Law"
            },
            {
                "name": "IRPF_Personal_Income_Tax",
                "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764",
                "type": "html",
                "description": "IRPF - Personal Income Tax Law"
            },
            {
                "name": "IVA_Value_Added_Tax",
                "url": "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740",
                "type": "html",
                "description": "IVA - Value Added Tax Law"
            },
            {
                "name": "Impuesto_Sociedades_Corporate_Tax",
                "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328",
                "type": "html",
                "description": "Impuesto sobre Sociedades - Corporate Tax Law"
            },
            {
                "name": "Impuesto_Sucesiones_Donaciones",
                "url": "https://www.boe.es/buscar/act.php?id=BOE-A-1987-28141",
                "type": "html",
                "description": "Impuesto sobre Sucesiones y Donaciones - Inheritance & Gift Tax"
            },
            {
                "name": "Impuesto_Patrimonio_Wealth_Tax",
                "url": "https://www.boe.es/buscar/act.php?id=BOE-A-1991-13292",
                "type": "html",
                "description": "Impuesto sobre el Patrimonio - Wealth Tax Law"
            }
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def download_document(self, doc_info: dict) -> bool:
        """Скачивает один документ"""
        try:
            print(f"\n📄 Скачиваем: {doc_info['name']}")
            print(f"   Описание: {doc_info['description']}")
            print(f"   URL: {doc_info['url']}")
            
            # Определяем расширение файла
            if doc_info['type'] == 'html':
                file_extension = '.html'
            else:
                file_extension = '.pdf'
            
            # Путь для сохранения
            file_path = self.download_dir / f"{doc_info['name']}{file_extension}"
            
            # Проверяем, не скачан ли уже
            if file_path.exists():
                print(f"   ⚠️  Файл уже существует: {file_path}")
                return True
            
            # Скачиваем
            response = self.session.get(doc_info['url'], timeout=30)
            response.raise_for_status()
            
            # Сохраняем
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"   ✅ Сохранено: {file_path}")
            print(f"   📊 Размер: {len(response.text)} символов")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Ошибка скачивания: {e}")
            return False
    
    def download_all(self) -> None:
        """Скачивает все документы"""
        print("🚀 Начинаем скачивание налоговых документов")
        print("=" * 60)
        
        success_count = 0
        total_count = len(self.documents)
        
        for i, doc in enumerate(self.documents, 1):
            print(f"\n[{i}/{total_count}]", end=" ")
            
            if self.download_document(doc):
                success_count += 1
            
            # Пауза между запросами
            if i < total_count:
                time.sleep(2)
        
        print("\n" + "=" * 60)
        print(f"📊 РЕЗУЛЬТАТЫ:")
        print(f"   Успешно: {success_count}/{total_count}")
        print(f"   Папка: {self.download_dir.absolute()}")
        
        if success_count == total_count:
            print("🎉 Все документы скачаны успешно!")
        else:
            print(f"⚠️  {total_count - success_count} документов не скачаны")
    
    def list_downloaded(self) -> None:
        """Показывает список скачанных файлов"""
        print("\n📁 Скачанные файлы:")
        print("-" * 40)
        
        if not self.download_dir.exists():
            print("   Папка не существует")
            return
        
        files = list(self.download_dir.glob("*"))
        if not files:
            print("   Файлы не найдены")
            return
        
        for file_path in sorted(files):
            size = file_path.stat().st_size
            size_mb = size / 1024 / 1024
            print(f"   📄 {file_path.name}")
            print(f"      Размер: {size_mb:.2f} MB")
            print(f"      Путь: {file_path}")


def main():
    """Основная функция"""
    downloader = TaxDocumentDownloader()
    
    print("🔍 TuExpertoFiscal NAIL - Скачивание налоговых документов")
    print("=" * 60)
    
    # Показываем список документов
    print("\n📋 Документы для скачивания:")
    for i, doc in enumerate(downloader.documents, 1):
        print(f"   {i}. {doc['name']} - {doc['description']}")
    
    # Скачиваем все
    downloader.download_all()
    
    # Показываем результат
    downloader.list_downloaded()


if __name__ == "__main__":
    main()
