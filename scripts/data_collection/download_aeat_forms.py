#!/usr/bin/env python3
"""
Скрипт для скачивания форм AEAT
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


class AEATFormsDownloader:
    """Класс для скачивания форм AEAT"""
    
    def __init__(self):
        self.settings = Settings()
        self.download_dir = Path("data/aeat_forms")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Список форм для скачивания
        self.forms = [
            {
                "name": "Modelo_303_IVA",
                "url": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimientos_ayuda/Modelos/Modelos_2024/303/303_2024.pdf",
                "type": "pdf",
                "description": "Modelo 303 - Declaración trimestral del IVA"
            },
            {
                "name": "Modelo_111_Retenciones",
                "url": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimientos_ayuda/Modelos/Modelos_2024/111/111_2024.pdf",
                "type": "pdf",
                "description": "Modelo 111 - Retenciones e ingresos a cuenta"
            },
            {
                "name": "Modelo_130_IRPF_Autonomos",
                "url": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimientos_ayuda/Modelos/Modelos_2024/130/130_2024.pdf",
                "type": "pdf",
                "description": "Modelo 130 - IRPF para autónomos (estimación directa)"
            },
            {
                "name": "Modelo_131_IRPF_Autonomos",
                "url": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimientos_ayuda/Modelos/Modelos_2024/131/131_2024.pdf",
                "type": "pdf",
                "description": "Modelo 131 - IRPF para autónomos (estimación objetiva)"
            },
            {
                "name": "Modelo_036_Alta_Autonomo",
                "url": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimientos_ayuda/Modelos/Modelos_2024/036/036_2024.pdf",
                "type": "pdf",
                "description": "Modelo 036 - Alta como autónomo"
            },
            {
                "name": "Modelo_037_Alta_Autonomo_Simplificado",
                "url": "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimientos_ayuda/Modelos/Modelos_2024/037/037_2024.pdf",
                "type": "pdf",
                "description": "Modelo 037 - Alta como autónomo (simplificado)"
            }
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def download_form(self, form_info: dict) -> bool:
        """Скачивает одну форму"""
        try:
            print(f"\n📄 Скачиваем: {form_info['name']}")
            print(f"   Описание: {form_info['description']}")
            print(f"   URL: {form_info['url']}")
            
            # Путь для сохранения
            file_path = self.download_dir / f"{form_info['name']}.pdf"
            
            # Проверяем, не скачан ли уже
            if file_path.exists():
                print(f"   ⚠️  Файл уже существует: {file_path}")
                return True
            
            # Скачиваем
            response = self.session.get(form_info['url'], timeout=30)
            response.raise_for_status()
            
            # Сохраняем как PDF
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"   ✅ Сохранено: {file_path}")
            print(f"   📊 Размер: {len(response.content)} байт")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Ошибка скачивания: {e}")
            return False
    
    def download_all(self) -> None:
        """Скачивает все формы"""
        print("🚀 Начинаем скачивание форм AEAT")
        print("=" * 60)
        
        success_count = 0
        total_count = len(self.forms)
        
        for i, form in enumerate(self.forms, 1):
            print(f"\n[{i}/{total_count}]", end=" ")
            
            if self.download_form(form):
                success_count += 1
            
            # Пауза между запросами
            if i < total_count:
                time.sleep(2)
        
        print("\n" + "=" * 60)
        print(f"📊 РЕЗУЛЬТАТЫ:")
        print(f"   Успешно: {success_count}/{total_count}")
        print(f"   Папка: {self.download_dir.absolute()}")
        
        if success_count == total_count:
            print("🎉 Все формы скачаны успешно!")
        else:
            print(f"⚠️  {total_count - success_count} форм не скачаны")
    
    def list_downloaded(self) -> None:
        """Показывает список скачанных файлов"""
        print("\n📁 Скачанные файлы:")
        print("-" * 40)
        
        if not self.download_dir.exists():
            print("   Папка не существует")
            return
        
        files = list(self.download_dir.glob("*.pdf"))
        if not files:
            print("   PDF файлы не найдены")
            return
        
        for file_path in sorted(files):
            size = file_path.stat().st_size
            size_mb = size / 1024 / 1024
            print(f"   📄 {file_path.name}")
            print(f"      Размер: {size_mb:.2f} MB")
            print(f"      Путь: {file_path}")


def main():
    """Основная функция"""
    downloader = AEATFormsDownloader()
    
    print("🔍 TuExpertoFiscal NAIL - Скачивание форм AEAT")
    print("=" * 60)
    
    # Показываем список форм
    print("\n📋 Формы для скачивания:")
    for i, form in enumerate(downloader.forms, 1):
        print(f"   {i}. {form['name']} - {form['description']}")
    
    # Скачиваем все
    downloader.download_all()
    
    # Показываем результат
    downloader.list_downloaded()


if __name__ == "__main__":
    main()
