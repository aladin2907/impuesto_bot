"""
Генерация embeddings через локальную модель HuggingFace
Модель: intfloat/multilingual-e5-large (1024 dimensions)
"""
from typing import List, Optional
from sentence_transformers import SentenceTransformer
import numpy as np


class HuggingFaceEmbeddings:
    """Генерация embeddings через локальную модель sentence-transformers"""

    def __init__(self):
        self.model_name = "intfloat/multilingual-e5-large"
        self.dimension = 1024

        print(f"⏳ Загрузка модели {self.model_name}...")
        # Загружаем модель локально (кэшируется после первого раза)
        self.model = SentenceTransformer(self.model_name)
        print(f"✅ Модель загружена!")

    def generate(self, text: str, prefix: str = "query: ") -> Optional[List[float]]:
        """
        Генерация embedding для текста

        Args:
            text: Текст для генерации embedding
            prefix: Префикс для E5 модели ("query: " для запросов, "passage: " для документов)

        Returns:
            Вектор embedding (1024 dimensions) или None
        """
        if not text or not text.strip():
            print("⚠️ Пустой текст, пропускаем")
            return None

        # E5 модели требуют префикс
        # "query: " для поисковых запросов
        # "passage: " для документов в базе
        prefixed_text = f"{prefix}{text}"

        try:
            # Генерируем embedding
            embedding = self.model.encode(prefixed_text, convert_to_numpy=True)

            # Конвертируем в список
            embedding_list = embedding.tolist()

            if len(embedding_list) == self.dimension:
                return embedding_list
            else:
                print(f"⚠️ Неверная размерность: {len(embedding_list)}, ожидалось {self.dimension}")
                return None

        except Exception as e:
            print(f"❌ Ошибка при генерации embedding: {e}")
            return None

    def generate_batch(
        self,
        texts: List[str],
        prefix: str = "passage: ",
        batch_size: int = 32,
        show_progress: bool = True
    ) -> List[Optional[List[float]]]:
        """
        Генерация embeddings для батча текстов (эффективнее чем по одному)

        Args:
            texts: Список текстов
            prefix: Префикс для E5 модели
            batch_size: Размер батча для обработки
            show_progress: Показывать прогресс

        Returns:
            Список векторов embeddings
        """
        # Добавляем префикс ко всем текстам
        prefixed_texts = [f"{prefix}{text}" for text in texts]

        try:
            # Батч-генерация (намного быстрее!)
            embeddings = self.model.encode(
                prefixed_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True
            )

            # Конвертируем в список списков
            embeddings_list = [emb.tolist() for emb in embeddings]

            return embeddings_list

        except Exception as e:
            print(f"❌ Ошибка при батч-генерации: {e}")
            return [None] * len(texts)


# Тестовая функция
def test_embeddings():
    """Тест генерации embeddings"""
    generator = HuggingFaceEmbeddings()

    test_text = "Какие налоги должен платить автономо в Испании?"
    print(f"Тестовый текст: {test_text}")

    embedding = generator.generate(test_text)

    if embedding:
        print(f"✅ Embedding успешно сгенерирован!")
        print(f"  Размерность: {len(embedding)}")
        print(f"  Первые 5 значений: {embedding[:5]}")
    else:
        print("❌ Не удалось сгенерировать embedding")


if __name__ == "__main__":
    test_embeddings()
