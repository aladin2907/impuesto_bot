#!/usr/bin/env python3
"""
Скрипт для скрапинга налоговых новостей из испанских источников
Источники: Expansion, Cinco Dias, El Economista
"""

import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict
import time


class NewsScrap:
    def __init__(self):
        self.sources = {
            "expansion": {
                "name": "Expansión",
                "url": "https://www.expansion.com/economia/fiscal.html",
                "selector": "article"
            },
            "cincodias": {
                "name": "Cinco Días",
                "url": "https://cincodias.elpais.com/noticias/fiscalidad/",
                "selector": "article"
            }
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def scrape_expansion(self, limit: int = 5) -> List[Dict]:
        """Скрапит новости с Expansion (demo)"""
        print(f"📰 Скрапим Expansion...")
        
        # Демо данные - в реальности нужно парсить сайт
        articles = [
            {
                "article_url": "https://www.expansion.com/economia/fiscal/2024/10/01/articulo1.html",
                "article_title": "Hacienda modifica el IRPF para 2025: estos son los cambios que afectan a autónomos",
                "news_source": "Expansión",
                "author": "Juan García",
                "published_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "summary": "La Agencia Tributaria introduce cambios en el IRPF que afectarán a los trabajadores autónomos a partir de 2025...",
                "content": """
                La Agencia Tributaria ha anunciado modificaciones importantes en el Impuesto sobre la Renta de las Personas Físicas (IRPF) 
                que entrarán en vigor en 2025. Estos cambios afectarán principalmente a los trabajadores autónomos.
                
                Entre las principales novedades se encuentra la actualización de las escalas de retención y nuevos límites para deducciones.
                Los autónomos que facturen menos de 15.000 euros al año podrán beneficiarse de reducciones adicionales.
                
                Además, se simplifica el proceso de declaración trimestral para facilitar el cumplimiento fiscal.
                """,
                "categories": ["irpf", "autonomos", "cambios_legislativos"],
                "keywords": ["irpf", "autónomos", "2025", "hacienda", "cambios"],
                "content_length": 450
            },
            {
                "article_url": "https://www.expansion.com/economia/fiscal/2024/09/28/articulo2.html",
                "article_title": "IVA: nuevas obligaciones para empresas desde octubre 2024",
                "news_source": "Expansión",
                "author": "María López",
                "published_at": (datetime.now() - timedelta(days=5)).isoformat(),
                "summary": "Las empresas tendrán que cumplir con nuevos requisitos de facturación electrónica obligatoria...",
                "content": """
                A partir de octubre de 2024, las empresas españolas deberán cumplir con nuevas obligaciones relacionadas con el IVA
                y la facturación electrónica. El sistema Verifactu se implementa de forma gradual.
                
                Todas las facturas deberán ser emitidas a través de sistemas certificados por la AEAT. Las empresas tendrán un periodo
                de adaptación de 6 meses para implementar los nuevos sistemas.
                
                El incumplimiento de estas obligaciones puede acarrear sanciones de hasta 10.000 euros.
                """,
                "categories": ["iva", "facturacion", "verifactu"],
                "keywords": ["iva", "facturación electrónica", "verifactu", "empresas"],
                "content_length": 380
            },
            {
                "article_url": "https://www.expansion.com/economia/fiscal/2024/09/25/articulo3.html",
                "article_title": "Modelo 303: guía completa para la declaración del IVA del tercer trimestre",
                "news_source": "Expansión",
                "author": "Carlos Martínez",
                "published_at": (datetime.now() - timedelta(days=8)).isoformat(),
                "summary": "Todo lo que necesitas saber para presentar correctamente el Modelo 303 correspondiente al tercer trimestre...",
                "content": """
                El plazo para presentar el Modelo 303 del tercer trimestre finaliza el 20 de octubre. Los autónomos y empresas 
                deben revisar todas sus facturas del periodo julio-septiembre.
                
                Es importante verificar que todas las facturas emitidas y recibidas estén correctamente registradas. Los errores 
                más comunes incluyen la incorrecta aplicación del tipo de IVA y la omisión de facturas.
                
                La AEAT recomienda usar el sistema de borradores para minimizar errores. Las sanciones por declaraciones incorrectas 
                pueden llegar al 20% del importe omitido.
                """,
                "categories": ["iva", "modelo_303", "guias"],
                "keywords": ["modelo 303", "iva", "tercer trimestre", "autónomos"],
                "content_length": 420
            },
            {
                "article_url": "https://www.expansion.com/economia/fiscal/2024/09/20/articulo4.html",
                "article_title": "Cotizaciones de autónomos: cambios en la base mínima para 2025",
                "news_source": "Expansión",
                "author": "Ana Rodríguez",
                "published_at": (datetime.now() - timedelta(days=13)).isoformat(),
                "summary": "La Seguridad Social anuncia el incremento de la base mínima de cotización para trabajadores autónomos...",
                "content": """
                La Seguridad Social ha confirmado que la base mínima de cotización para autónomos aumentará en 2025.
                Este cambio forma parte del nuevo sistema de cotización por ingresos reales.
                
                Los autónomos que coticen por la base mínima pagarán aproximadamente 310 euros mensuales, un incremento
                del 3.8% respecto a 2024. Sin embargo, quienes declaren ingresos bajos podrán beneficiarse de reducciones.
                
                El sistema permite ajustar la base de cotización hasta 6 veces al año para adaptarse a las fluctuaciones
                de ingresos de los autónomos.
                """,
                "categories": ["seguridad_social", "autonomos", "cotizaciones"],
                "keywords": ["autónomos", "cotizaciones", "seguridad social", "2025"],
                "content_length": 410
            },
            {
                "article_url": "https://www.expansion.com/economia/fiscal/2024/09/15/articulo5.html",
                "article_title": "Renta 2024: novedades en deducciones para trabajadores autónomos",
                "news_source": "Expansión",
                "author": "Pedro Sánchez",
                "published_at": (datetime.now() - timedelta(days=18)).isoformat(),
                "summary": "La declaración de la renta 2024 incluye nuevas deducciones para gastos de suministros y material de oficina...",
                "content": """
                Los autónomos podrán deducir un mayor porcentaje de gastos en la próxima declaración de la renta.
                Entre las novedades destacan las deducciones por teletrabajo y gastos de formación.
                
                Se podrá deducir hasta el 30% de los gastos de suministros del hogar si se trabaja desde casa, siempre
                que se disponga de un espacio dedicado exclusivamente a la actividad profesional.
                
                También se amplían las deducciones por inversión en digitalización y ciberseguridad, con límites
                de hasta 2.000 euros anuales.
                """,
                "categories": ["irpf", "deducciones", "autonomos"],
                "keywords": ["renta", "deducciones", "autónomos", "irpf"],
                "content_length": 395
            }
        ]
        
        print(f"✅ Найдено {len(articles)} статей")
        return articles[:limit]
    
    def scrape_cincodias(self, limit: int = 5) -> List[Dict]:
        """Скрапит новости с Cinco Dias (demo)"""
        print(f"📰 Скрапим Cinco Días...")
        
        articles = [
            {
                "article_url": "https://cincodias.elpais.com/2024/09/28/articulo1.html",
                "article_title": "El Gobierno aprueba beneficios fiscales para startups y emprendedores",
                "news_source": "Cinco Días",
                "author": "Laura Fernández",
                "published_at": (datetime.now() - timedelta(days=4)).isoformat(),
                "summary": "Nuevas deducciones fiscales para empresas tecnológicas y emprendedores en fase inicial...",
                "content": """
                El Consejo de Ministros ha aprobado un paquete de medidas fiscales destinadas a impulsar el ecosistema
                de startups en España. Las empresas de reciente creación podrán beneficiarse de reducciones en el
                Impuesto de Sociedades.
                
                Las startups tecnológicas tendrán un tipo reducido del 15% en el Impuesto de Sociedades durante
                los primeros cuatro años de actividad, en lugar del 25% habitual.
                
                Además, se introducen deducciones por la contratación de personal altamente cualificado y por
                inversión en I+D+i.
                """,
                "categories": ["sociedades", "startups", "deducciones"],
                "keywords": ["startups", "impuesto sociedades", "deducciones", "emprendedores"],
                "content_length": 430
            },
            {
                "article_url": "https://cincodias.elpais.com/2024/09/22/articulo2.html",
                "article_title": "Calendario fiscal de octubre 2024: todas las fechas clave",
                "news_source": "Cinco Días",
                "author": "Roberto Gómez",
                "published_at": (datetime.now() - timedelta(days=10)).isoformat(),
                "summary": "Resumen de todas las obligaciones fiscales que vencen en octubre para autónomos y empresas...",
                "content": """
                Octubre es un mes clave en el calendario fiscal español. Los autónomos y empresas deben estar atentos
                a múltiples vencimientos.
                
                El 20 de octubre vence el plazo para presentar el Modelo 303 (IVA trimestral) y el Modelo 111
                (retenciones). El 30 de octubre es el límite para el Modelo 130 (pago fraccionado IRPF).
                
                Es fundamental planificar con antelación para evitar recargos y sanciones. La presentación fuera
                de plazo puede suponer un recargo del 5% al 20% según el retraso.
                """,
                "categories": ["calendario_fiscal", "obligaciones"],
                "keywords": ["calendario", "octubre", "vencimientos", "modelo 303"],
                "content_length": 405
            },
            {
                "article_url": "https://cincodias.elpais.com/2024/09/18/articulo3.html",
                "article_title": "Sociedades limitadas: nuevas obligaciones contables desde 2025",
                "news_source": "Cinco Días",
                "author": "Isabel Torres",
                "published_at": (datetime.now() - timedelta(days=14)).isoformat(),
                "summary": "Las SL deberán presentar información adicional sobre su estructura de beneficiarios...",
                "content": """
                A partir de 2025, las sociedades limitadas españolas tendrán que cumplir con nuevas obligaciones
                de transparencia fiscal. Deberán reportar información detallada sobre sus beneficiarios finales.
                
                Esta medida forma parte de las directivas europeas contra el blanqueo de capitales. Las empresas
                deberán actualizar sus datos en el Registro Mercantil.
                
                El incumplimiento de estas obligaciones puede conllevar sanciones de hasta 30.000 euros para
                las empresas y responsabilidad personal para los administradores.
                """,
                "categories": ["sociedades", "transparencia", "obligaciones"],
                "keywords": ["sociedades limitadas", "beneficiarios", "transparencia"],
                "content_length": 390
            }
        ]
        
        print(f"✅ Найдено {len(articles)} статей")
        return articles[:limit]
    
    def scrape_all_sources(self, limit_per_source: int = 5) -> List[Dict]:
        """Скрапит новости со всех источников"""
        all_articles = []
        
        all_articles.extend(self.scrape_expansion(limit_per_source))
        time.sleep(1)  # Пауза между запросами
        all_articles.extend(self.scrape_cincodias(limit_per_source))
        
        return all_articles
    
    def save_to_json(self, articles: List[Dict], output_file: str):
        """Сохраняет новости в JSON"""
        data = {
            "scraped_at": datetime.now().isoformat(),
            "total_articles": len(articles),
            "sources": list(set(a['news_source'] for a in articles)),
            "articles": articles
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Сохранено в {output_file}")
    
    def analyze_articles(self, articles: List[Dict]):
        """Анализирует структуру новостей"""
        print(f"\n{'='*60}")
        print("АНАЛИЗ НОВОСТЕЙ")
        print(f"{'='*60}")
        
        # Источники
        sources = {}
        for article in articles:
            source = article['news_source']
            sources[source] = sources.get(source, 0) + 1
        
        print(f"\n📰 Источники ({len(sources)}):")
        for source, count in sorted(sources.items()):
            print(f"  - {source}: {count} статей")
        
        # Категории
        all_categories = set()
        for article in articles:
            all_categories.update(article.get('categories', []))
        
        print(f"\n🏷️ Категории ({len(all_categories)}):")
        for category in sorted(all_categories):
            count = sum(1 for a in articles if category in a.get('categories', []))
            print(f"  - {category}: {count} статей")
        
        # Ключевые слова
        from collections import Counter
        all_keywords = []
        for article in articles:
            all_keywords.extend(article.get('keywords', []))
        
        keyword_counts = Counter(all_keywords)
        print(f"\n🔑 Топ ключевых слов:")
        for keyword, count in keyword_counts.most_common(10):
            print(f"  - {keyword}: {count}")
        
        # Примеры статей
        print(f"\n📝 Примеры статей:")
        for i, article in enumerate(articles[:3], 1):
            print(f"\n  {i}. {article['article_title']}")
            print(f"     Источник: {article['news_source']}")
            print(f"     Дата: {article['published_at'][:10]}")
            print(f"     Категории: {', '.join(article.get('categories', []))}")
            print(f"     Длина: {article.get('content_length', 0)} символов")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Скрапинг налоговых новостей')
    parser.add_argument('--limit', type=int, default=5, help='Количество статей с каждого источника')
    parser.add_argument('--output', default='data/news_articles.json', help='Файл для сохранения')
    
    args = parser.parse_args()
    
    scraper = NewsScrap()
    
    # Скрапим новости
    articles = scraper.scrape_all_sources(args.limit)
    
    # Анализируем
    scraper.analyze_articles(articles)
    
    # Сохраняем
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    scraper.save_to_json(articles, args.output)


if __name__ == "__main__":
    main()

