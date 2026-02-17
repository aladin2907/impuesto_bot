"""
DocumentSearch - инструмент для целевого поиска в документах

Используется когда нужен более глубокий поиск по конкретной теме
в PDF документах, законодательной базе, или новостях
"""
import time
from typing import Optional, List
from app.models.agent import ToolType, ToolResult, QueryType
from app.services.agent.tools.base_tool import BaseTool
from app.repositories.pdf_repository import PDFRepository
from app.repositories.news_repository import NewsRepository
from app.services.embeddings.huggingface_embeddings import HuggingFaceEmbeddings


class DocumentSearch(BaseTool):
    """Инструмент для глубокого поиска в документах"""

    def __init__(self):
        super().__init__(ToolType.DOCUMENT_SEARCH)
        self.pdf_repo = PDFRepository()
        self.news_repo = NewsRepository()
        self.embeddings = HuggingFaceEmbeddings()

    def should_run(self, query: str, query_type: str) -> bool:
        """Запускать для юридических вопросов и поиска в законах"""
        if query_type in [QueryType.LEGAL_INTERPRETATION, QueryType.NEWS_UPDATE]:
            return True

        q = query.lower()
        doc_keywords = [
            'ley', 'artículo', 'articulo', 'normativa', 'reglamento',
            'boe', 'dogv', 'real decreto', 'orden ministerial',
            'закон', 'статья', 'норматив', 'документ',
            'sentencia', 'jurisprudencia', 'tribunal',
            'noticia', 'actualidad', 'cambio', 'novedad', 'nuevo',
            'новост', 'изменение', 'обновление',
        ]
        return any(kw in q for kw in doc_keywords)

    async def execute(self, **kwargs) -> ToolResult:
        """Поиск в документах"""
        start = time.time()
        query = kwargs.get('query', '')
        search_type = kwargs.get('search_type', 'all')  # 'pdf', 'news', 'all'

        try:
            q = query.lower()
            results = []

            # Определяем что искать
            should_search_pdf = search_type in ['pdf', 'all']
            should_search_news = search_type in ['news', 'all']

            # Если в запросе есть "noticia", "новость" - только новости
            if any(kw in q for kw in ['noticia', 'новост', 'actualidad', 'cambio reciente']):
                should_search_pdf = False
                should_search_news = True

            # Если упомянуты законы/статьи - только PDF
            if any(kw in q for kw in ['ley', 'artículo', 'boe', 'закон', 'статья']):
                should_search_pdf = True
                should_search_news = False

            # Поиск в PDF документах
            if should_search_pdf:
                pdf_results = await self._search_pdfs(query)
                if pdf_results:
                    results.append(pdf_results)

            # Поиск в новостях
            if should_search_news:
                news_results = await self._search_news(query)
                if news_results:
                    results.append(news_results)

            if not results:
                return self._success(
                    "No he encontrado documentos específicos relacionados con tu consulta. "
                    "Intenta reformular la pregunta con términos más específicos.",
                    (time.time() - start) * 1000
                )

            final_result = "\n\n---\n\n".join(results)
            return self._success(final_result, (time.time() - start) * 1000)

        except Exception as e:
            return self._error(str(e), (time.time() - start) * 1000)

    async def _search_pdfs(self, query: str) -> Optional[str]:
        """Поиск в PDF документах"""
        try:
            # Генерируем эмбеддинг для запроса (OpenAI для PDF)
            from app.services.embeddings.openai_embeddings import OpenAIEmbeddings
            openai_emb = OpenAIEmbeddings()
            embedding = await openai_emb.embed_query(query)

            # Гибридный поиск
            results = await self.pdf_repo.hybrid_search(
                query_text=query,
                query_embedding=embedding,
                match_limit=5,
                similarity_threshold=0.35
            )

            if not results:
                return None

            lines = ["**📄 Documentos legales encontrados:**", ""]

            for i, doc in enumerate(results, 1):
                title = doc.get('document_title', 'Documento sin título')
                content = doc.get('content', '')[:400]
                category = doc.get('category', '')
                region = doc.get('region', '')
                url = doc.get('url', '')
                similarity = doc.get('similarity', 0)

                lines.append(f"{i}. **{title}**")
                if category:
                    lines.append(f"   Categoría: {category}")
                if region:
                    lines.append(f"   Región: {region}")
                lines.append(f"   Relevancia: {similarity:.1%}")
                lines.append(f"   _{content}_")
                if url:
                    lines.append(f"   🔗 {url}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return f"Error buscando en documentos PDF: {e}"

    async def _search_news(self, query: str) -> Optional[str]:
        """Поиск в новостях"""
        try:
            # Генерируем эмбеддинг для запроса (OpenAI для News)
            from app.services.embeddings.openai_embeddings import OpenAIEmbeddings
            openai_emb = OpenAIEmbeddings()
            embedding = await openai_emb.embed_query(query)

            # Гибридный поиск
            results = await self.news_repo.hybrid_search(
                query_text=query,
                query_embedding=embedding,
                match_limit=5,
                similarity_threshold=0.35
            )

            if not results:
                # Пробуем получить последние новости
                results = await self.news_repo.get_recent_news(limit=3)

            if not results:
                return None

            lines = ["**📰 Noticias y actualizaciones encontradas:**", ""]

            for i, article in enumerate(results, 1):
                title = article.get('article_title', 'Sin título')
                summary = article.get('summary', article.get('content', ''))[:300]
                published = article.get('published_date', '')
                source = article.get('source', '')
                url = article.get('url', '')
                similarity = article.get('similarity', 0)

                lines.append(f"{i}. **{title}**")
                if published:
                    lines.append(f"   Fecha: {published}")
                if source:
                    lines.append(f"   Fuente: {source}")
                if similarity > 0:
                    lines.append(f"   Relevancia: {similarity:.1%}")
                lines.append(f"   _{summary}_")
                if url:
                    lines.append(f"   🔗 {url}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return f"Error buscando en noticias: {e}"
