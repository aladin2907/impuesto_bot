#!/usr/bin/env python3
"""
Скрипт для поиска актуальных ссылок на формы AEAT
"""

import os
import sys
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
import time
import re

# Добавляем корневую папку в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import Settings


class AEATFormsFinder:
    """Класс для поиска актуальных ссылок на формы AEAT"""
    
    def __init__(self):
        self.settings = Settings()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Базовые URL для поиска
        self.base_urls = [
            "https://sede.agenciatributaria.gob.es/",
            "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimientos_ayuda/Modelos/",
            "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimientos_ayuda/Modelos/Modelos_2025/",
            "https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimientos_ayuda/Modelos/Modelos_2024/",
        ]
        
        # Формы для поиска
        self.target_forms = [
            "303",  # IVA
            "111",  # Retenciones
            "130",  # IRPF Autónomos
            "131",  # IRPF Autónomos
            "036",  # Alta Autónomo
            "037",  # Alta Autónomo Simplificado
        ]
    
    def search_forms_on_page(self, url: str) -> list:
        """Ищет ссылки на формы на странице"""
        try:
            print(f"🔍 Ищем формы на: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Ищем ссылки на PDF файлы
            pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', response.text, re.IGNORECASE)
            
            found_forms = []
            for link in pdf_links:
                # Проверяем, содержит ли ссылка номер формы
                for form_num in self.target_forms:
                    if form_num in link:
                        full_url = urljoin(url, link)
                        found_forms.append({
                            "form": form_num,
                            "url": full_url,
                            "source": url
                        })
                        print(f"   ✅ Найдена форма {form_num}: {full_url}")
            
            return found_forms
            
        except Exception as e:
            print(f"   ❌ Ошибка поиска на {url}: {e}")
            return []
    
    def test_form_url(self, form_info: dict) -> bool:
        """Тестирует доступность ссылки на форму"""
        try:
            response = self.session.head(form_info["url"], timeout=10)
            if response.status_code == 200:
                print(f"   ✅ Форма {form_info['form']} доступна")
                return True
            else:
                print(f"   ❌ Форма {form_info['form']} недоступна: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Ошибка тестирования формы {form_info['form']}: {e}")
            return False
    
    def find_all_forms(self) -> list:
        """Ищет все формы на всех базовых URL"""
        print("🚀 Поиск актуальных ссылок на формы AEAT")
        print("=" * 60)
        
        all_forms = []
        
        for base_url in self.base_urls:
            forms = self.search_forms_on_page(base_url)
            all_forms.extend(forms)
            time.sleep(1)  # Пауза между запросами
        
        # Убираем дубликаты
        unique_forms = {}
        for form in all_forms:
            form_num = form["form"]
            if form_num not in unique_forms:
                unique_forms[form_num] = form
        
        print(f"\n📊 Найдено уникальных форм: {len(unique_forms)}")
        
        # Тестируем доступность
        print("\n🔍 Тестируем доступность форм:")
        working_forms = []
        for form_num, form_info in unique_forms.items():
            if self.test_form_url(form_info):
                working_forms.append(form_info)
        
        return working_forms
    
    def download_working_forms(self, forms: list) -> None:
        """Скачивает рабочие формы"""
        if not forms:
            print("❌ Нет рабочих форм для скачивания")
            return
        
        download_dir = Path("data/aeat_forms")
        download_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📥 Скачиваем {len(forms)} форм:")
        
        for form_info in forms:
            try:
                form_num = form_info["form"]
                url = form_info["url"]
                
                print(f"\n📄 Скачиваем форму {form_num}")
                print(f"   URL: {url}")
                
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Сохраняем
                filename = f"Modelo_{form_num}_AEAT.pdf"
                file_path = download_dir / filename
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"   ✅ Сохранено: {file_path}")
                print(f"   📊 Размер: {len(response.content)} байт")
                
            except Exception as e:
                print(f"   ❌ Ошибка скачивания формы {form_num}: {e}")
            
            time.sleep(2)  # Пауза между скачиваниями


def main():
    """Основная функция"""
    finder = AEATFormsFinder()
    
    print("🔍 TuExpertoFiscal NAIL - Поиск форм AEAT")
    print("=" * 60)
    
    # Ищем формы
    working_forms = finder.find_all_forms()
    
    if working_forms:
        print(f"\n✅ Найдено {len(working_forms)} рабочих форм:")
        for form in working_forms:
            print(f"   📄 Форма {form['form']}: {form['url']}")
        
        # Скачиваем
        finder.download_working_forms(working_forms)
    else:
        print("\n❌ Рабочие формы не найдены")
        print("💡 Попробуйте поискать вручную на сайте AEAT")


if __name__ == "__main__":
    main()
