-- Отключение RLS для всех таблиц (если нужно открыть доступ для n8n)
-- ВНИМАНИЕ: Это делает данные публично доступными через API!
-- Используйте только если n8n использует service_role ключ

ALTER TABLE public.telegram_threads_content DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.calendar_deadlines DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.pdf_documents_content DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.news_articles_content DISABLE ROW LEVEL SECURITY;

-- Или если хотите разрешить только чтение для всех:
-- ALTER TABLE public.telegram_threads_content ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Allow anonymous read access" ON public.telegram_threads_content FOR SELECT USING (true);
