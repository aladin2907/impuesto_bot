# 🆕 What's New - Latest Updates

## 🚀 CI/CD Pipeline (October 30, 2025)

**Теперь деплой полностью автоматический!**

Просто:
```bash
git add .
git commit -m "your changes"
git push origin main
```

И через 6 минут твои изменения **автоматически** на production! 🎉

### Как это работает:
1. **Push** → GitHub Actions триггерится
2. **Build** на серверах GitHub (не твой сервер!)
3. **Push** образа в GitHub Container Registry
4. **Deploy** на production через SSH
5. **Done!** ✅

### Где смотреть:
- **Actions**: https://github.com/aladin2907/impuesto_bot/actions
- **API**: http://63.180.170.54/docs

---

## 🧠 Telegram Hybrid Search (October 30, 2025)

**75,000+ Telegram threads теперь с embeddings!**

### До:
- ❌ Только 6.6% тредов с embeddings
- ❌ Плохое качество semantic search
- ❌ Дорогие OpenAI embeddings

### После:
- ✅ 100% тредов с embeddings
- ✅ Отличное качество поиска
- ✅ **БЕСПЛАТНЫЕ** HuggingFace embeddings
- ✅ Hybrid search (kNN + BM25)
- ✅ Мультиязычный поиск (RU, ES, EN, UK)

### Производительность:
- Telegram search: **862ms**
- PDF search: **4129ms**
- ALL sources: **1711ms**

---

## 📚 Что почитать:

### Quick Start:
- **CICD_QUICKSTART.md** - Настройка CI/CD (3 мин)
- **QUICK_START_WEBHOOK.txt** - Как использовать API

### Detailed:
- **docs/CICD_SETUP.md** - Полная документация CI/CD
- **docs/EMBEDDINGS_STRATEGY.md** - Стратегия embeddings
- **docs/DEPLOYMENT_SUCCESS_REPORT.md** - Отчет о деплое

---

## 🔥 Основные фишки:

1. **Zero-downtime deployment** - API не падает при обновлении
2. **Multi-model embeddings** - Разные модели для разных источников
3. **Hybrid search** - Semantic (kNN) + Keyword (BM25)
4. **Multilingual** - RU, ES, EN, UK support
5. **Free embeddings** - HuggingFace API для Telegram
6. **Auto-deploy** - Push = Deploy

---

## 🎯 Следующие шаги:

### Сейчас работает:
- ✅ Telegram search (75K threads)
- ✅ PDF search (4 tax laws)
- ✅ Calendar search (2025-2026)
- ✅ News search (limited data)

### Можно добавить:
- [ ] Больше новостей
- [ ] AEAT forms
- [ ] Valencia DOGV
- [ ] Мониторинг и алерты
- [ ] Redis кэш

---

**Последний деплой:** October 30, 2025  
**Статус:** ✅ All systems operational  
**API:** http://63.180.170.54  

